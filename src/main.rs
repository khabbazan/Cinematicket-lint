mod config;
mod rules;
mod util;

use std::path::{Path, PathBuf};

use rayon::prelude::*;
use regex::Regex;
use ruff_python_ast::token::{Token, TokenKind};
use ruff_python_parser::parse_module;
use ruff_source_file::LineIndex;
use ruff_text_size::Ranged;
use serde_json::Value;

use util::{Ctx, Violation};

fn suppressions(ctx: &Ctx, tokens: &[Token]) -> (Vec<String>, std::collections::HashMap<usize, Vec<String>>) {
    let directive = Regex::new(r"ctlint:\s*(CT\d+(?:\s*,\s*CT\d+)*)").unwrap();
    let code = Regex::new(r"CT\d+").unwrap();
    let mut by_line: std::collections::HashMap<usize, Vec<String>> = Default::default();
    for token in tokens {
        if token.kind() != TokenKind::Comment {
            continue;
        }
        let text = &ctx.source[token.range()];
        if let Some(m) = directive.captures(text) {
            let line = ctx.line(token.start());
            by_line.entry(line).or_default().extend(code.find_iter(&m[1]).map(|c| c.as_str().to_string()));
        }
    }
    let file_wide = by_line.get(&1).cloned().unwrap_or_default();
    (file_wide, by_line)
}

fn check_file(path: &Path, config: &Value) -> Vec<Violation> {
    if path.extension().is_none_or(|e| e != "py") {
        return Vec::new();
    }
    let Ok(source) = std::fs::read_to_string(path) else { return Vec::new() };
    let Ok(parsed) = parse_module(&source) else { return Vec::new() };
    let path_text = path.to_string_lossy().into_owned();
    let body = &parsed.syntax().body;
    let ctx = Ctx { path: &path_text, source: &source, body, index: LineIndex::from_source_text(&source) };
    let tokens = parsed.tokens();

    let mut violations: Vec<Violation> = Vec::new();
    violations.extend(rules::ct01(&ctx, tokens));
    violations.extend(rules::ct02(&ctx));
    violations.extend(rules::ct03(&ctx));
    violations.extend(rules::ct04_06(&ctx));
    violations.extend(rules::ct07(&ctx));
    violations.extend(rules::ct08(&ctx));
    violations.extend(rules::ct09(&ctx));

    type Check = fn(&Ctx, &Value) -> Vec<Violation>;
    let configurable: [(&str, Check); 9] = [
        ("name_length", rules::ct10),
        ("bad_names", rules::ct11),
        ("module_constant_naming", rules::ct12),
        ("keyword_before_vararg", |c, _| rules::ct13(c)),
        ("instance_attribute_count", rules::ct14),
        ("attribute_outside_init", rules::ct15),
        ("local_variable_count", rules::ct16),
        ("module_line_count", rules::ct17),
        ("redefined_outer_name", rules::ct18),
    ];
    let empty = Value::Object(Default::default());
    for (key, check) in configurable {
        let options = config.get(key).unwrap_or(&empty);
        if options.get("enabled").and_then(Value::as_bool).unwrap_or(true) {
            violations.extend(check(&ctx, options));
        }
    }

    if violations.is_empty() {
        return violations;
    }
    let (file_wide, by_line) = suppressions(&ctx, tokens);
    violations
        .into_iter()
        .filter(|v| {
            !file_wide.iter().any(|c| c == v.code)
                && !by_line.get(&v.line).is_some_and(|codes| codes.iter().any(|c| c == v.code))
        })
        .collect()
}

fn main() {
    let cwd = std::env::current_dir().unwrap_or_default();
    let (config, pyproject) = config::load_config(&cwd);
    let matchers = config::exclude_matchers(&config::string_list(&config, "exclude"));
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    let paths: Vec<PathBuf> = if arguments.is_empty() {
        config::discover_files(&config, pyproject.as_deref(), &cwd)
    } else {
        arguments.iter().map(PathBuf::from).collect()
    };

    let results: Vec<Vec<Violation>> = paths
        .par_iter()
        .map(|p| if config::is_excluded(p, &matchers) { Vec::new() } else { check_file(p, &config) })
        .collect();

    let mut found = false;
    for violation in results.into_iter().flatten() {
        found = true;
        println!("{}:{}: {} {}", violation.path, violation.line, violation.code, violation.message);
    }
    std::process::exit(i32::from(found));
}
