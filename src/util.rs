//! Shared helpers: violation type, parse context, scope walking.

use std::collections::{HashSet, VecDeque};

use regex::Regex;
use ruff_python_ast::visitor::{walk_expr, walk_except_handler, walk_stmt, Visitor};
use ruff_python_ast::{
    ExceptHandler, Expr, ExprContext, Parameter, Stmt, StmtClassDef, StmtFunctionDef,
};
use ruff_source_file::LineIndex;
use ruff_text_size::{Ranged, TextSize};
use serde_json::Value;

pub struct Violation {
    pub path: String,
    pub line: usize,
    pub code: &'static str,
    pub message: String,
}

pub struct Ctx<'a> {
    pub path: &'a str,
    pub source: &'a str,
    pub body: &'a [Stmt],
    pub index: LineIndex,
}

impl<'a> Ctx<'a> {
    pub fn line(&self, offset: TextSize) -> usize {
        self.index.line_index(offset).get()
    }

    pub fn violation(&self, line: usize, code: &'static str, message: String) -> Violation {
        Violation { path: self.path.to_string(), line, code, message }
    }
}

// ---- options -----------------------------------------------------------------------------

pub fn opt_str(options: &Value, key: &str, default: &str) -> String {
    options.get(key).and_then(Value::as_str).unwrap_or(default).to_string()
}

pub fn opt_usize(options: &Value, key: &str, default: usize) -> usize {
    options.get(key).and_then(Value::as_u64).map(|n| n as usize).unwrap_or(default)
}

pub fn opt_bool(options: &Value, key: &str, default: bool) -> bool {
    options.get(key).and_then(Value::as_bool).unwrap_or(default)
}

pub fn opt_vec(options: &Value, key: &str, default: &[&str]) -> Vec<String> {
    match options.get(key).and_then(Value::as_array) {
        Some(items) => items.iter().filter_map(|v| v.as_str().map(str::to_string)).collect(),
        None => default.iter().map(|s| s.to_string()).collect(),
    }
}

/// Python `re.match` semantics: anchored at the start, not necessarily at the end.
pub fn compile_match(pattern: &str) -> Regex {
    Regex::new(&format!(r"\A(?:{pattern})")).unwrap_or_else(|_| Regex::new(r"\A\z.\A").unwrap())
}

// ---- tree walking -------------------------------------------------------------------------

/// Child statements of `stmt` in field order (functions and classes included, expressions not).
pub fn child_stmts(stmt: &Stmt) -> Vec<&Stmt> {
    let mut out: Vec<&Stmt> = Vec::new();
    match stmt {
        Stmt::FunctionDef(f) => out.extend(f.body.iter()),
        Stmt::ClassDef(c) => out.extend(c.body.iter()),
        Stmt::If(i) => {
            out.extend(i.body.iter());
            for clause in &i.elif_else_clauses {
                out.extend(clause.body.iter());
            }
        }
        Stmt::For(f) => {
            out.extend(f.body.iter());
            out.extend(f.orelse.iter());
        }
        Stmt::While(w) => {
            out.extend(w.body.iter());
            out.extend(w.orelse.iter());
        }
        Stmt::With(w) => out.extend(w.body.iter()),
        Stmt::Try(t) => {
            out.extend(t.body.iter());
            for handler in &t.handlers {
                let ExceptHandler::ExceptHandler(h) = handler;
                out.extend(h.body.iter());
            }
            out.extend(t.orelse.iter());
            out.extend(t.finalbody.iter());
        }
        Stmt::Match(m) => {
            for case in &m.cases {
                out.extend(case.body.iter());
            }
        }
        _ => {}
    }
    out
}

pub fn all_functions(body: &[Stmt]) -> Vec<&StmtFunctionDef> {
    let mut queue: VecDeque<&Stmt> = body.iter().collect();
    let mut out = Vec::new();
    while let Some(stmt) = queue.pop_front() {
        if let Stmt::FunctionDef(f) = stmt {
            out.push(f);
        }
        queue.extend(child_stmts(stmt));
    }
    out
}

pub fn all_classes(body: &[Stmt]) -> Vec<&StmtClassDef> {
    let mut queue: VecDeque<&Stmt> = body.iter().collect();
    let mut out = Vec::new();
    while let Some(stmt) = queue.pop_front() {
        if let Stmt::ClassDef(c) = stmt {
            out.push(c);
        }
        queue.extend(child_stmts(stmt));
    }
    out
}

/// Module-level statements, entering `if`/`try`/`with` blocks but never functions or classes.
pub fn module_level_statements(body: &[Stmt]) -> Vec<&Stmt> {
    fn visit<'a>(stmts: &'a [Stmt], out: &mut Vec<&'a Stmt>) {
        for stmt in stmts {
            out.push(stmt);
            match stmt {
                Stmt::If(i) => {
                    visit(&i.body, out);
                    for clause in &i.elif_else_clauses {
                        visit(&clause.body, out);
                    }
                }
                Stmt::Try(t) => {
                    visit(&t.body, out);
                    for handler in &t.handlers {
                        let ExceptHandler::ExceptHandler(h) = handler;
                        visit(&h.body, out);
                    }
                    visit(&t.orelse, out);
                    visit(&t.finalbody, out);
                }
                Stmt::With(w) => visit(&w.body, out),
                _ => {}
            }
        }
    }
    let mut out = Vec::new();
    visit(body, &mut out);
    out
}

/// Plain names inside an assignment target (tuple/list/starred unpacking included).
pub fn target_names<'a>(target: &'a Expr, out: &mut Vec<&'a ruff_python_ast::ExprName>) {
    match target {
        Expr::Name(n) => out.push(n),
        Expr::Tuple(t) => t.elts.iter().for_each(|e| target_names(e, out)),
        Expr::List(l) => l.elts.iter().for_each(|e| target_names(e, out)),
        Expr::Starred(s) => target_names(&s.value, out),
        _ => {}
    }
}

pub fn func_line(ctx: &Ctx, f: &StmtFunctionDef) -> usize {
    ctx.line(f.name.range().start())
}

pub fn class_line(ctx: &Ctx, c: &StmtClassDef) -> usize {
    ctx.line(c.name.range().start())
}

/// Parameters in Python's `ast` order: positional-only + regular, `*args`, keyword-only, `**kwargs`.
pub fn parameters(f: &StmtFunctionDef) -> Vec<&Parameter> {
    let p = &f.parameters;
    let mut out: Vec<&Parameter> = p.posonlyargs.iter().chain(p.args.iter()).map(|a| &a.parameter).collect();
    if let Some(v) = &p.vararg {
        out.push(v);
    }
    out.extend(p.kwonlyargs.iter().map(|a| &a.parameter));
    if let Some(k) = &p.kwarg {
        out.push(k);
    }
    out
}

// ---- function scope ----------------------------------------------------------------------

pub struct Scope {
    /// Names bound in the function's own scope (parameters excluded), first occurrence order.
    pub bound: Vec<(String, usize)>,
    /// Names declared `global` / `nonlocal`.
    pub outer: HashSet<String>,
}

struct Collector<'c, 'a> {
    ctx: &'c Ctx<'a>,
    bound: Vec<(String, usize)>,
    seen: HashSet<String>,
    outer: HashSet<String>,
}

impl Collector<'_, '_> {
    fn add(&mut self, name: &str, line: usize) {
        if self.seen.insert(name.to_string()) {
            self.bound.push((name.to_string(), line));
        }
    }
}

impl<'a> Visitor<'a> for Collector<'_, '_> {
    fn visit_stmt(&mut self, stmt: &'a Stmt) {
        match stmt {
            Stmt::FunctionDef(f) => {
                let line = func_line(self.ctx, f);
                self.add(f.name.as_str(), line);
            }
            Stmt::ClassDef(c) => {
                let line = class_line(self.ctx, c);
                self.add(c.name.as_str(), line);
            }
            Stmt::Global(g) => g.names.iter().for_each(|n| {
                self.outer.insert(n.as_str().to_string());
            }),
            Stmt::Nonlocal(g) => g.names.iter().for_each(|n| {
                self.outer.insert(n.as_str().to_string());
            }),
            Stmt::Import(i) => {
                let line = self.ctx.line(i.range().start());
                for alias in &i.names {
                    let name = alias.asname.as_ref().unwrap_or(&alias.name).as_str();
                    self.add(name.split('.').next().unwrap_or(name), line);
                }
            }
            Stmt::ImportFrom(i) => {
                let line = self.ctx.line(i.range().start());
                for alias in &i.names {
                    let name = alias.asname.as_ref().unwrap_or(&alias.name).as_str();
                    self.add(name.split('.').next().unwrap_or(name), line);
                }
            }
            _ => walk_stmt(self, stmt),
        }
    }

    fn visit_expr(&mut self, expr: &'a Expr) {
        match expr {
            Expr::Lambda(_) | Expr::ListComp(_) | Expr::SetComp(_) | Expr::DictComp(_) | Expr::Generator(_) => {}
            Expr::Name(n) if matches!(n.ctx, ExprContext::Store) => {
                let line = self.ctx.line(n.range().start());
                self.add(n.id.as_str(), line);
            }
            _ => walk_expr(self, expr),
        }
    }

    fn visit_except_handler(&mut self, handler: &'a ExceptHandler) {
        let ExceptHandler::ExceptHandler(h) = handler;
        if let Some(name) = &h.name {
            let line = self.ctx.line(h.range().start());
            self.add(name.as_str(), line);
        }
        walk_except_handler(self, handler);
    }
}

pub fn scope_of(ctx: &Ctx, f: &StmtFunctionDef) -> Scope {
    let mut collector = Collector { ctx, bound: Vec::new(), seen: HashSet::new(), outer: HashSet::new() };
    for stmt in f.body.iter() {
        collector.visit_stmt(stmt);
    }
    let outer = collector.outer;
    let bound = collector.bound.into_iter().filter(|(n, _)| !outer.contains(n)).collect();
    Scope { bound, outer }
}
