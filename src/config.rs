//! `[tool.cinematicket_lint]` loading, file discovery and exclusion.

use std::path::{Path, PathBuf};

use globset::GlobBuilder;
use serde_json::Value;

fn find_pyproject(start: &Path) -> Option<PathBuf> {
    let current = std::fs::canonicalize(start).unwrap_or_else(|_| start.to_path_buf());
    let from = if current.is_dir() { current } else { current.parent()?.to_path_buf() };
    from.ancestors().map(|d| d.join("pyproject.toml")).find(|c| c.is_file())
}

pub fn load_config(start: &Path) -> (Value, Option<PathBuf>) {
    let Some(path) = find_pyproject(start) else { return (Value::Object(Default::default()), None) };
    let parsed = std::fs::read_to_string(&path)
        .ok()
        .and_then(|text| text.parse::<toml::Table>().ok())
        .and_then(|table| serde_json::to_value(table).ok());
    let config = parsed
        .as_ref()
        .and_then(|v| v.get("tool"))
        .and_then(|v| v.get("cinematicket_lint"))
        .cloned()
        .unwrap_or_else(|| Value::Object(Default::default()));
    (config, Some(path))
}

pub fn string_list(config: &Value, key: &str) -> Vec<String> {
    config
        .get(key)
        .and_then(Value::as_array)
        .map(|items| items.iter().filter_map(|v| v.as_str().map(str::to_string)).collect())
        .unwrap_or_default()
}

pub fn discover_files(config: &Value, pyproject: Option<&Path>, cwd: &Path) -> Vec<PathBuf> {
    let root = pyproject.and_then(Path::parent).map(Path::to_path_buf).unwrap_or_else(|| cwd.to_path_buf());
    let mut files = Vec::new();
    for include in string_list(config, "include") {
        let mut found: Vec<PathBuf> = walkdir::WalkDir::new(root.join(include))
            .into_iter()
            .filter_map(Result::ok)
            .filter(|e| e.file_type().is_file() && e.path().extension().is_some_and(|x| x == "py"))
            .map(|e| e.into_path())
            .collect();
        found.sort();
        files.extend(found);
    }
    files
}

/// Mirrors `name in path.parts or path.match(name)` on the resolved path.
pub fn is_excluded(path: &Path, matchers: &[(String, Option<globset::GlobMatcher>)]) -> bool {
    let resolved = std::fs::canonicalize(path).unwrap_or_else(|_| {
        if path.is_absolute() { path.to_path_buf() } else { std::env::current_dir().unwrap_or_default().join(path) }
    });
    let parts: Vec<String> = resolved.components().map(|c| c.as_os_str().to_string_lossy().into_owned()).collect();
    matchers.iter().any(|(name, glob)| {
        if parts.iter().any(|p| p == name) {
            return true;
        }
        let Some(glob) = glob else { return false };
        let wanted = name.split('/').filter(|s| !s.is_empty()).count().max(1);
        if parts.len() < wanted {
            return false;
        }
        let tail = parts[parts.len() - wanted..].join("/");
        glob.is_match(&tail)
    })
}

pub fn exclude_matchers(names: &[String]) -> Vec<(String, Option<globset::GlobMatcher>)> {
    names
        .iter()
        .map(|n| {
            let glob = GlobBuilder::new(n).literal_separator(true).build().ok().map(|g| g.compile_matcher());
            (n.clone(), glob)
        })
        .collect()
}
