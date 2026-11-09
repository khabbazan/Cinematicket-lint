//! The CT01-CT18 checks. Each takes the parse context and the rule's options (a JSON object).

use std::collections::{HashMap, HashSet};

use regex::Regex;
use ruff_python_ast::visitor::{walk_expr, walk_parameter, walk_stmt, Visitor};
use ruff_python_ast::{
    ExceptHandler, Expr, ExprContext, Keyword, Operator, Parameter, Stmt, StmtClassDef, UnaryOp,
};
use ruff_python_ast::token::{Token, TokenKind};
use ruff_text_size::Ranged;
use serde_json::Value;

use crate::util::*;

// =============================== CT01: backslash continuation ===============================

pub fn ct01(ctx: &Ctx, tokens: &[Token]) -> Vec<Violation> {
    let mut string_spans: Vec<(usize, usize)> = Vec::new();
    let mut depth: i64 = 0;
    let mut depth_by_line: HashMap<usize, i64> = HashMap::new();
    let mut fstring_start: Option<usize> = None;
    for token in tokens {
        let start_line = ctx.line(token.start());
        let end_line = ctx.line(token.end());
        match token.kind() {
            TokenKind::String => {
                if start_line != end_line {
                    string_spans.push((start_line, end_line));
                }
            }
            TokenKind::FStringStart => fstring_start = Some(start_line),
            TokenKind::FStringEnd => {
                if let Some(start) = fstring_start.take() {
                    if start != end_line {
                        string_spans.push((start, end_line));
                    }
                }
            }
            TokenKind::Lpar | TokenKind::Lsqb | TokenKind::Lbrace => depth += 1,
            TokenKind::Rpar | TokenKind::Rsqb | TokenKind::Rbrace => depth -= 1,
            _ => {}
        }
        depth_by_line.insert(start_line, depth);
    }

    let mut out = Vec::new();
    for (index, raw) in ctx.source.lines().enumerate() {
        let line_number = index + 1;
        if !raw.trim_end().ends_with('\\') {
            continue;
        }
        if string_spans.iter().any(|(s, e)| *s <= line_number && line_number <= *e) {
            continue;
        }
        if depth_by_line.get(&line_number).copied().unwrap_or(0) > 0 {
            continue;
        }
        out.push(ctx.violation(
            line_number,
            "CT01",
            "backslash line continuation is not allowed, use parentheses instead".to_string(),
        ));
    }
    out
}

// =============================== CT02: variable annotation ==================================

fn is_literal_expr(value: &Expr) -> bool {
    match value {
        Expr::StringLiteral(_)
        | Expr::BytesLiteral(_)
        | Expr::NumberLiteral(_)
        | Expr::BooleanLiteral(_)
        | Expr::NoneLiteral(_)
        | Expr::EllipsisLiteral(_)
        | Expr::List(_)
        | Expr::Tuple(_)
        | Expr::Dict(_)
        | Expr::Set(_)
        | Expr::FString(_) => true,
        Expr::UnaryOp(u) => {
            matches!(u.op, UnaryOp::USub | UnaryOp::UAdd) && matches!(&*u.operand, Expr::NumberLiteral(_))
        }
        _ => false,
    }
}

fn looks_like_constructor_call(value: &Expr) -> bool {
    let Expr::Call(call) = value else { return false };
    let first_upper = |name: &str| name.chars().next().is_some_and(char::is_uppercase);
    match &*call.func {
        Expr::Name(n) => first_upper(n.id.as_str()),
        Expr::Attribute(a) => first_upper(a.attr.as_str()),
        _ => false,
    }
}

/// Statements of a function's own scope, in the order the Python implementation yields them.
fn scope_statements<'a>(stmts: &'a [Stmt], out: &mut Vec<&'a Stmt>) {
    for stmt in stmts {
        out.push(stmt);
        match stmt {
            Stmt::FunctionDef(_) | Stmt::ClassDef(_) | Stmt::Match(_) => {}
            Stmt::If(i) => {
                scope_statements(&i.body, out);
                // `elif`/`else` chains are nested `If` statements in Python's tree.
                for clause in &i.elif_else_clauses {
                    scope_statements(&clause.body, out);
                }
            }
            Stmt::For(f) => {
                scope_statements(&f.body, out);
                scope_statements(&f.orelse, out);
            }
            Stmt::While(w) => {
                scope_statements(&w.body, out);
                scope_statements(&w.orelse, out);
            }
            Stmt::With(w) => scope_statements(&w.body, out),
            Stmt::Try(t) => {
                scope_statements(&t.body, out);
                scope_statements(&t.orelse, out);
                scope_statements(&t.finalbody, out);
                for handler in &t.handlers {
                    let ExceptHandler::ExceptHandler(h) = handler;
                    scope_statements(&h.body, out);
                }
            }
            _ => {}
        }
    }
}

pub fn ct02(ctx: &Ctx) -> Vec<Violation> {
    let mut out = Vec::new();
    for function in all_functions(ctx.body) {
        let mut statements = Vec::new();
        scope_statements(&function.body, &mut statements);

        let mut annotated: HashSet<&str> = HashSet::new();
        let p = &function.parameters;
        for param in p.posonlyargs.iter().chain(p.args.iter()).chain(p.kwonlyargs.iter()) {
            if param.parameter.annotation.is_some() {
                annotated.insert(param.parameter.name.as_str());
            }
        }
        for extra in [&p.vararg, &p.kwarg].into_iter().flatten() {
            if extra.annotation.is_some() {
                annotated.insert(extra.name.as_str());
            }
        }
        for stmt in &statements {
            if let Stmt::AnnAssign(a) = stmt {
                if let Expr::Name(n) = &*a.target {
                    annotated.insert(n.id.as_str());
                }
            }
        }

        for stmt in &statements {
            let Stmt::Assign(assign) = stmt else { continue };
            if assign.targets.len() != 1 {
                continue;
            }
            let Expr::Name(target) = &assign.targets[0] else { continue };
            if annotated.contains(target.id.as_str()) {
                continue;
            }
            if looks_like_constructor_call(&assign.value) || is_literal_expr(&assign.value) {
                continue;
            }
            out.push(ctx.violation(
                ctx.line(assign.range().start()),
                "CT02",
                format!(
                    "variable '{}' has no type annotation and its value is neither a class constructor call nor a literal data-type initialization",
                    target.id
                ),
            ));
        }
    }
    out
}

// =============================== CT03: optional default =====================================

fn is_none(expr: &Expr) -> bool {
    matches!(expr, Expr::NoneLiteral(_))
}

fn is_optional_annotation(annotation: &Expr) -> bool {
    match annotation {
        Expr::Subscript(s) => match &*s.value {
            Expr::Name(n) => n.id.as_str() == "Optional",
            Expr::Attribute(a) => a.attr.as_str() == "Optional",
            _ => false,
        },
        Expr::BinOp(b) if matches!(b.op, Operator::BitOr) => is_none(&b.left) || is_none(&b.right),
        _ => false,
    }
}

fn base_name(expr: &Expr) -> &str {
    match expr {
        Expr::Name(n) => n.id.as_str(),
        Expr::Attribute(a) => a.attr.as_str(),
        _ => "",
    }
}

pub fn ct03(ctx: &Ctx) -> Vec<Violation> {
    let mut out = Vec::new();
    for class in all_classes(ctx.body) {
        let is_model = class
            .arguments
            .as_ref()
            .is_some_and(|args| args.args.iter().any(|base| base_name(base) == "BaseModel"));
        if !is_model {
            continue;
        }
        for stmt in class.body.iter() {
            let Stmt::AnnAssign(a) = stmt else { continue };
            if a.value.is_some() || !is_optional_annotation(&a.annotation) {
                continue;
            }
            let field = match &*a.target {
                Expr::Name(n) => n.id.as_str(),
                _ => "<field>",
            };
            out.push(ctx.violation(
                ctx.line(a.range().start()),
                "CT03",
                format!("optional field '{field}' has no default value"),
            ));
        }
    }
    out
}

// =============================== CT04-CT06: OpenAPI schemas =================================

struct SchemaCalls<'a> {
    calls: Vec<&'a ruff_python_ast::ExprCall>,
}

impl<'a> Visitor<'a> for SchemaCalls<'a> {
    fn visit_expr(&mut self, expr: &'a Expr) {
        if let Expr::Call(call) = expr {
            if is_openapi_schema_call(call) {
                self.calls.push(call);
            }
        }
        walk_expr(self, expr);
    }
}

fn is_openapi_schema_call(call: &ruff_python_ast::ExprCall) -> bool {
    let Expr::Attribute(attr) = &*call.func else { return false };
    if !matches!(attr.attr.as_str(), "Schema" | "Parameter") {
        return false;
    }
    matches!(&*attr.value, Expr::Name(n) if n.id.as_str() == "openapi")
}

fn imports_openapi(body: &[Stmt]) -> bool {
    struct Finder(bool);
    impl<'a> Visitor<'a> for Finder {
        fn visit_stmt(&mut self, stmt: &'a Stmt) {
            if let Stmt::ImportFrom(i) = stmt {
                if i.module.as_ref().is_some_and(|m| m.as_str() == "drf_yasg") && i.names.iter().any(|a| a.name.as_str() == "openapi") {
                    self.0 = true;
                }
            }
            walk_stmt(self, stmt);
        }
    }
    let mut finder = Finder(false);
    for stmt in body {
        finder.visit_stmt(stmt);
    }
    finder.0
}

struct AllCalls<'a> {
    calls: Vec<&'a ruff_python_ast::ExprCall>,
    response_ids: HashSet<usize>,
}

impl<'a> Visitor<'a> for AllCalls<'a> {
    fn visit_stmt(&mut self, stmt: &'a Stmt) {
        if let Stmt::Assign(assign) = stmt {
            let is_response = assign.targets.iter().any(|t| matches!(t, Expr::Name(n) if n.id.as_str().to_uppercase().contains("RESPONSE")));
            if is_response {
                let mut nested = SchemaCalls { calls: Vec::new() };
                nested.visit_expr(&assign.value);
                for call in nested.calls {
                    self.response_ids.insert(call as *const _ as usize);
                }
            }
        }
        walk_stmt(self, stmt);
    }

    fn visit_expr(&mut self, expr: &'a Expr) {
        if let Expr::Call(call) = expr {
            if is_openapi_schema_call(call) {
                self.calls.push(call);
            }
        }
        walk_expr(self, expr);
    }
}

fn find_keyword<'a>(call: &'a ruff_python_ast::ExprCall, name: &str) -> Option<&'a Keyword> {
    call.arguments.keywords.iter().find(|k| k.arg.as_ref().is_some_and(|a| a.as_str() == name))
}

fn ends_with_period(value: &Expr) -> bool {
    match value {
        Expr::StringLiteral(s) => s.value.to_str().trim_end().ends_with('.'),
        _ => true,
    }
}

pub fn ct04_06(ctx: &Ctx) -> Vec<Violation> {
    if !imports_openapi(ctx.body) {
        return Vec::new();
    }
    let mut all = AllCalls { calls: Vec::new(), response_ids: HashSet::new() };
    for stmt in ctx.body {
        all.visit_stmt(stmt);
    }
    let mut out = Vec::new();
    for call in all.calls {
        let require_example = all.response_ids.contains(&(call as *const _ as usize));
        let line = ctx.line(call.range().start());
        let description = find_keyword(call, "description");
        let example = find_keyword(call, "example");
        if require_example && example.is_none() {
            out.push(ctx.violation(line, "CT04", "missing example=".to_string()));
        }
        match description {
            None => out.push(ctx.violation(line, "CT05", "missing description=".to_string())),
            Some(keyword) => {
                if !ends_with_period(&keyword.value) {
                    out.push(ctx.violation(
                        ctx.line(keyword.value.range().start()),
                        "CT06",
                        "description must end with a period".to_string(),
                    ));
                }
            }
        }
    }
    out
}

// =============================== CT07: test names ===========================================

fn test_name_regex() -> Regex {
    Regex::new(r"^test_(success|failure)(_|$)").unwrap()
}

pub fn ct07(ctx: &Ctx) -> Vec<Violation> {
    let file_name = std::path::Path::new(ctx.path).file_name().and_then(|n| n.to_str()).unwrap_or("");
    if !file_name.starts_with("test_") {
        return Vec::new();
    }
    let valid = test_name_regex();
    let mut out = Vec::new();
    for function in all_functions(ctx.body) {
        let name = function.name.as_str();
        if !name.starts_with("test_") || valid.is_match(name) {
            continue;
        }
        out.push(ctx.violation(
            func_line(ctx, function),
            "CT07",
            format!("test function '{name}' must be named test_success or test_success_..., or test_failure or test_failure_..."),
        ));
    }
    out
}

// =============================== CT08 / CT09: annotations ===================================

pub fn ct08(ctx: &Ctx) -> Vec<Violation> {
    let mut out = Vec::new();
    for function in all_functions(ctx.body) {
        let p = &function.parameters;
        for param in p.posonlyargs.iter().chain(p.args.iter()).chain(p.kwonlyargs.iter()) {
            let name = param.parameter.name.as_str();
            if name == "self" || name == "cls" || param.parameter.annotation.is_some() {
                continue;
            }
            out.push(ctx.violation(
                ctx.line(param.parameter.name.range().start()),
                "CT08",
                format!("parameter '{name}' of function '{}' has no type annotation", function.name),
            ));
        }
    }
    out
}

pub fn ct09(ctx: &Ctx) -> Vec<Violation> {
    let exempt_test = test_name_regex();
    let dunder = Regex::new(r"^__.+__$").unwrap();
    let mut out = Vec::new();
    for function in all_functions(ctx.body) {
        let name = function.name.as_str();
        if exempt_test.is_match(name) || dunder.is_match(name) || function.returns.is_some() {
            continue;
        }
        out.push(ctx.violation(
            func_line(ctx, function),
            "CT09",
            format!("function '{name}' has no return type annotation"),
        ));
    }
    out
}

// =============================== CT10: name length ==========================================

pub fn ct10(ctx: &Ctx, options: &Value) -> Vec<Violation> {
    let variable_pattern = opt_str(options, "variable_pattern", "^[a-z_][a-z0-9_]+$");
    let argument_pattern = opt_str(options, "argument_pattern", "^[a-z_][a-z0-9_]+$");
    let good_names = opt_vec(options, "good_names", &["ex", "Run", "_", "pk"]);
    let variable_regex = compile_match(&variable_pattern);
    let argument_regex = compile_match(&argument_pattern);
    let invalid = |name: &str, regex: &Regex| !good_names.iter().any(|g| g == name) && !regex.is_match(name);

    let mut out = Vec::new();
    for function in all_functions(ctx.body) {
        for param in parameters(function) {
            let name = param.name.as_str();
            if invalid(name, &argument_regex) {
                out.push(ctx.violation(
                    ctx.line(param.name.range().start()),
                    "CT10",
                    format!("parameter name '{name}' does not match the required pattern {argument_pattern}"),
                ));
            }
        }
        for (name, line) in scope_of(ctx, function).bound {
            if invalid(&name, &variable_regex) {
                out.push(ctx.violation(
                    line,
                    "CT10",
                    format!("variable name '{name}' does not match the required pattern {variable_pattern}"),
                ));
            }
        }
    }
    out
}

// =============================== CT11: bad names ============================================

struct DeclaredNames<'c, 'a> {
    ctx: &'c Ctx<'a>,
    names: Vec<(String, usize)>,
}

impl<'a> Visitor<'a> for DeclaredNames<'_, '_> {
    fn visit_stmt(&mut self, stmt: &'a Stmt) {
        match stmt {
            Stmt::FunctionDef(f) => self.names.push((f.name.as_str().to_string(), func_line(self.ctx, f))),
            Stmt::ClassDef(c) => self.names.push((c.name.as_str().to_string(), class_line(self.ctx, c))),
            _ => {}
        }
        walk_stmt(self, stmt);
    }

    fn visit_expr(&mut self, expr: &'a Expr) {
        if let Expr::Name(n) = expr {
            if matches!(n.ctx, ExprContext::Store) {
                self.names.push((n.id.as_str().to_string(), self.ctx.line(n.range().start())));
            }
        }
        walk_expr(self, expr);
    }

    fn visit_parameter(&mut self, parameter: &'a Parameter) {
        self.names.push((parameter.name.as_str().to_string(), self.ctx.line(parameter.name.range().start())));
        walk_parameter(self, parameter);
    }

    fn visit_except_handler(&mut self, handler: &'a ExceptHandler) {
        let ExceptHandler::ExceptHandler(h) = handler;
        if let Some(name) = &h.name {
            self.names.push((name.as_str().to_string(), self.ctx.line(h.range().start())));
        }
        ruff_python_ast::visitor::walk_except_handler(self, handler);
    }
}

pub fn ct11(ctx: &Ctx, options: &Value) -> Vec<Violation> {
    let bad: HashSet<String> =
        opt_vec(options, "names", &["foo", "bar", "baz", "toto", "tutu", "tata"]).into_iter().collect();
    let mut declared = DeclaredNames { ctx, names: Vec::new() };
    for stmt in ctx.body {
        declared.visit_stmt(stmt);
    }
    declared
        .names
        .into_iter()
        .filter(|(name, _)| bad.contains(name))
        .map(|(name, line)| ctx.violation(line, "CT11", format!("name '{name}' is not allowed")))
        .collect()
}

// =============================== CT12: module constants =====================================

fn is_py_constant(expr: &Expr) -> bool {
    matches!(
        expr,
        Expr::StringLiteral(_)
            | Expr::BytesLiteral(_)
            | Expr::NumberLiteral(_)
            | Expr::BooleanLiteral(_)
            | Expr::NoneLiteral(_)
            | Expr::EllipsisLiteral(_)
    )
}

fn is_constant_value(expr: &Expr) -> bool {
    match expr {
        Expr::UnaryOp(u) => is_constant_value(&u.operand),
        Expr::BinOp(b) => is_constant_value(&b.left) && is_constant_value(&b.right),
        other => is_py_constant(other),
    }
}

pub fn ct12(ctx: &Ctx, options: &Value) -> Vec<Violation> {
    let pattern = opt_str(options, "pattern", "^_*[A-Z][A-Z0-9_]*$");
    let allowed = opt_vec(options, "allowed_names", &[]);
    let only_constants = opt_bool(options, "only_constant_values", true);
    let pattern_regex = compile_match(&pattern);
    let dunder = Regex::new(r"^__.+__$").unwrap();
    let pascal = Regex::new(r"^_*[A-Z][a-z0-9]+[A-Za-z0-9]*$").unwrap();

    let mut out = Vec::new();
    for stmt in module_level_statements(ctx.body) {
        let (targets, value): (Vec<&Expr>, &Expr) = match stmt {
            Stmt::Assign(a) => (a.targets.iter().collect(), &a.value),
            Stmt::AnnAssign(a) if a.value.is_some() => (vec![&*a.target], a.value.as_deref().unwrap()),
            _ => continue,
        };
        if only_constants && !is_constant_value(value) {
            continue;
        }
        for target in targets {
            let mut names = Vec::new();
            target_names(target, &mut names);
            for name in names {
                let id = name.id.as_str();
                let exempt = allowed.iter().any(|a| a == id)
                    || dunder.is_match(id)
                    || pattern_regex.is_match(id)
                    || (pascal.is_match(id) && !is_py_constant(value));
                if exempt {
                    continue;
                }
                out.push(ctx.violation(
                    ctx.line(name.range().start()),
                    "CT12",
                    format!("module-level constant '{id}' does not match the required pattern {pattern}"),
                ));
            }
        }
    }
    out
}

// =============================== CT13: keyword before *args =================================

pub fn ct13(ctx: &Ctx) -> Vec<Violation> {
    let mut out = Vec::new();
    for function in all_functions(ctx.body) {
        let p = &function.parameters;
        let Some(vararg) = &p.vararg else { continue };
        let has_default = p.posonlyargs.iter().chain(p.args.iter()).any(|a| a.default.is_some());
        if !has_default {
            continue;
        }
        out.push(ctx.violation(
            func_line(ctx, function),
            "CT13",
            format!("function '{}' has a parameter with a default value before *{}", function.name, vararg.name),
        ));
    }
    out
}

// =============================== CT14 / CT15: instance attributes ===========================

enum Node<'a> {
    Stmt(&'a Stmt),
    Handler(&'a ruff_python_ast::ExceptHandlerExceptHandler),
}

fn node_children<'a>(node: &Node<'a>) -> Vec<Node<'a>> {
    match node {
        Node::Handler(h) => h.body.iter().map(Node::Stmt).collect(),
        Node::Stmt(stmt) => match stmt {
            Stmt::ClassDef(_) => Vec::new(),
            Stmt::Try(t) => {
                let mut out: Vec<Node> = t.body.iter().map(Node::Stmt).collect();
                for handler in &t.handlers {
                    let ExceptHandler::ExceptHandler(h) = handler;
                    out.push(Node::Handler(h));
                }
                out.extend(t.orelse.iter().map(Node::Stmt));
                out.extend(t.finalbody.iter().map(Node::Stmt));
                out
            }
            other => child_stmts(other).into_iter().map(Node::Stmt).collect(),
        },
    }
}

fn attribute_targets<'a>(target: &'a Expr, out: &mut Vec<&'a ruff_python_ast::ExprAttribute>) {
    match target {
        Expr::Attribute(a) => out.push(a),
        Expr::Tuple(t) => t.elts.iter().for_each(|e| attribute_targets(e, out)),
        Expr::List(l) => l.elts.iter().for_each(|e| attribute_targets(e, out)),
        Expr::Starred(s) => attribute_targets(&s.value, out),
        _ => {}
    }
}

/// attribute name -> [(method name, line)], ordered like the Python implementation (LIFO stack walk).
fn instance_attributes(ctx: &Ctx, class: &StmtClassDef) -> Vec<(String, Vec<(String, usize)>)> {
    let mut order: Vec<String> = Vec::new();
    let mut map: HashMap<String, Vec<(String, usize)>> = HashMap::new();
    for statement in class.body.iter() {
        let Stmt::FunctionDef(method) = statement else { continue };
        let Some(first) = method.parameters.args.first() else { continue };
        let is_class_or_static = method.decorator_list.iter().any(
            |d| matches!(&d.expression, Expr::Name(n) if matches!(n.id.as_str(), "classmethod" | "staticmethod")),
        );
        if is_class_or_static {
            continue;
        }
        let receiver = first.parameter.name.as_str();
        let mut stack: Vec<Node> = method.body.iter().map(Node::Stmt).collect();
        while let Some(node) = stack.pop() {
            if let Node::Stmt(stmt) = &node {
                let targets: Vec<&Expr> = match stmt {
                    Stmt::Assign(a) => a.targets.iter().collect(),
                    Stmt::AnnAssign(a) => vec![&*a.target],
                    Stmt::AugAssign(a) => vec![&*a.target],
                    _ => Vec::new(),
                };
                for target in targets {
                    let mut attributes = Vec::new();
                    attribute_targets(target, &mut attributes);
                    for attribute in attributes {
                        if matches!(&*attribute.value, Expr::Name(n) if n.id.as_str() == receiver) {
                            let name = attribute.attr.as_str().to_string();
                            if !map.contains_key(&name) {
                                order.push(name.clone());
                            }
                            map.entry(name).or_default().push((method.name.as_str().to_string(), ctx.line(attribute.range().start())));
                        }
                    }
                }
            }
            stack.extend(node_children(&node));
        }
    }
    order.into_iter().map(|name| { let v = map.remove(&name).unwrap(); (name, v) }).collect()
}

pub fn ct14(ctx: &Ctx, options: &Value) -> Vec<Violation> {
    let maximum = opt_usize(options, "max", 7);
    let mut out = Vec::new();
    for class in all_classes(ctx.body) {
        let count = instance_attributes(ctx, class).len();
        if count > maximum {
            out.push(ctx.violation(
                class_line(ctx, class),
                "CT14",
                format!("class '{}' has {count} instance attributes (max {maximum})", class.name),
            ));
        }
    }
    out
}

fn class_level_names(class: &StmtClassDef) -> HashSet<String> {
    let mut names = HashSet::new();
    for statement in class.body.iter() {
        match statement {
            Stmt::Assign(a) => {
                for target in &a.targets {
                    if let Expr::Name(n) = target {
                        names.insert(n.id.as_str().to_string());
                    }
                }
            }
            Stmt::AnnAssign(a) => {
                if let Expr::Name(n) = &*a.target {
                    names.insert(n.id.as_str().to_string());
                }
            }
            Stmt::FunctionDef(f) => {
                names.insert(f.name.as_str().to_string());
            }
            Stmt::ClassDef(c) => {
                names.insert(c.name.as_str().to_string());
            }
            _ => {}
        }
    }
    names
}

fn defined_names(
    ctx: &Ctx,
    class: &StmtClassDef,
    local_classes: &HashMap<String, &StmtClassDef>,
    defining_methods: &HashSet<String>,
    seen: &HashSet<String>,
) -> Option<HashSet<String>> {
    let mut defined = class_level_names(class);
    for (attribute, assignments) in instance_attributes(ctx, class) {
        if assignments.iter().any(|(method, _)| defining_methods.contains(method)) {
            defined.insert(attribute);
        }
    }
    if let Some(arguments) = &class.arguments {
        for base in &arguments.args {
            if matches!(base, Expr::Name(n) if n.id.as_str() == "object") {
                continue;
            }
            let Expr::Name(base_name) = base else { return None };
            let Some(base_class) = local_classes.get(base_name.id.as_str()) else { return None };
            if seen.contains(base_name.id.as_str()) {
                return None;
            }
            let mut next_seen = seen.clone();
            next_seen.insert(class.name.as_str().to_string());
            let inherited = defined_names(ctx, base_class, local_classes, defining_methods, &next_seen)?;
            defined.extend(inherited);
        }
    }
    Some(defined)
}

pub fn ct15(ctx: &Ctx, options: &Value) -> Vec<Violation> {
    let defining_vec = opt_vec(options, "defining_methods", &["__init__", "__new__", "setUp", "__post_init__"]);
    let defining_methods: HashSet<String> = defining_vec.iter().cloned().collect();
    let mut described = defining_vec.clone();
    described.sort();
    let described = described.join(" / ");
    let local_classes: HashMap<String, &StmtClassDef> = ctx
        .body
        .iter()
        .filter_map(|s| if let Stmt::ClassDef(c) = s { Some((c.name.as_str().to_string(), c)) } else { None })
        .collect();

    let mut out = Vec::new();
    for class in all_classes(ctx.body) {
        let Some(defined) = defined_names(ctx, class, &local_classes, &defining_methods, &HashSet::new()) else { continue };
        for (attribute, assignments) in instance_attributes(ctx, class) {
            if defined.contains(&attribute) {
                continue;
            }
            out.push(ctx.violation(
                assignments[0].1,
                "CT15",
                format!("attribute '{attribute}' of class '{}' is defined outside {described}", class.name),
            ));
        }
    }
    out
}

// =============================== CT16: local variable count =================================

pub fn ct16(ctx: &Ctx, options: &Value) -> Vec<Violation> {
    let maximum = opt_usize(options, "max", 15);
    let ignored_regex = compile_match(&opt_str(options, "ignored_argument_pattern", "_.*|^ignored_|^unused_"));
    let mut out = Vec::new();
    for function in all_functions(ctx.body) {
        let scope = scope_of(ctx, function);
        let parameter_names: HashSet<&str> =
            parameters(function).into_iter().map(|p| p.name.as_str()).filter(|n| !scope.outer.contains(*n)).collect();
        let mut names: HashSet<&str> = parameter_names.clone();
        names.extend(scope.bound.iter().map(|(n, _)| n.as_str()));
        let ignored = parameter_names.iter().filter(|n| ignored_regex.is_match(n)).count();
        let count = names.len() - ignored;
        if count > maximum {
            out.push(ctx.violation(
                func_line(ctx, function),
                "CT16",
                format!("function '{}' has {count} local variables (max {maximum})", function.name),
            ));
        }
    }
    out
}

// =============================== CT17: module line count ====================================

pub fn ct17(ctx: &Ctx, options: &Value) -> Vec<Violation> {
    let maximum = opt_usize(options, "max", 1000);
    let count = ctx.source.lines().count();
    if count <= maximum {
        return Vec::new();
    }
    vec![ctx.violation(1, "CT17", format!("module has {count} lines (max {maximum})"))]
}

// =============================== CT18: redefined outer name =================================

fn module_level_names(ctx: &Ctx) -> HashMap<String, usize> {
    let mut names: HashMap<String, usize> = HashMap::new();
    for stmt in module_level_statements(ctx.body) {
        match stmt {
            Stmt::FunctionDef(f) => {
                names.entry(f.name.as_str().to_string()).or_insert(func_line(ctx, f));
            }
            Stmt::ClassDef(c) => {
                names.entry(c.name.as_str().to_string()).or_insert(class_line(ctx, c));
            }
            Stmt::Import(i) => {
                for alias in &i.names {
                    let name = alias.asname.as_ref().unwrap_or(&alias.name).as_str();
                    names.entry(name.split('.').next().unwrap_or(name).to_string()).or_insert(ctx.line(i.range().start()));
                }
            }
            Stmt::ImportFrom(i) => {
                for alias in &i.names {
                    let name = alias.asname.as_ref().unwrap_or(&alias.name).as_str();
                    names.entry(name.split('.').next().unwrap_or(name).to_string()).or_insert(ctx.line(i.range().start()));
                }
            }
            Stmt::Assign(a) => {
                for target in &a.targets {
                    let mut found = Vec::new();
                    target_names(target, &mut found);
                    for n in found {
                        names.entry(n.id.as_str().to_string()).or_insert(ctx.line(n.range().start()));
                    }
                }
            }
            Stmt::AnnAssign(a) => {
                let mut found = Vec::new();
                target_names(&a.target, &mut found);
                for n in found {
                    names.entry(n.id.as_str().to_string()).or_insert(ctx.line(n.range().start()));
                }
            }
            _ => {}
        }
    }
    names
}

pub fn ct18(ctx: &Ctx, options: &Value) -> Vec<Violation> {
    let ignored: HashSet<String> = opt_vec(options, "ignored_names", &[]).into_iter().collect();
    let module_names: HashMap<String, usize> =
        module_level_names(ctx).into_iter().filter(|(n, _)| !ignored.contains(n)).collect();
    let mut out = Vec::new();
    for function in all_functions(ctx.body) {
        let scope = scope_of(ctx, function);
        let mut candidates: Vec<(String, usize)> = Vec::new();
        let mut seen: HashSet<String> = HashSet::new();
        for param in parameters(function) {
            let name = param.name.as_str().to_string();
            if seen.insert(name.clone()) {
                candidates.push((name, ctx.line(param.name.range().start())));
            }
        }
        for (name, line) in scope.bound {
            if seen.insert(name.clone()) {
                candidates.push((name, line));
            }
        }
        for (name, line) in candidates {
            if let Some(module_line) = module_names.get(&name) {
                if !scope.outer.contains(&name) {
                    out.push(ctx.violation(
                        line,
                        "CT18",
                        format!("'{name}' redefines a name from the outer scope (line {module_line})"),
                    ));
                }
            }
        }
    }
    out
}
