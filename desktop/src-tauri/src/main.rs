#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;

#[tauri::command]
fn app_runtime(
    action: String,
    project_id: Option<String>,
    run_id: Option<String>,
    job_id: Option<String>,
    limit: Option<u32>,
    dry_run: Option<bool>,
    global_enabled: Option<bool>,
    project_enabled: Option<bool>,
    backend: Option<String>,
    search_top_k: Option<u32>,
    search_threshold: Option<f64>,
    provider_id: Option<String>,
    env_values: Option<serde_json::Value>,
    preferred: Option<bool>,
    prompt: Option<String>,
    project_name: Option<String>,
    project_path: Option<String>,
    primary_agent: Option<String>,
) -> Result<String, String> {
    let python = std::env::var("AOP_DESKTOP_PYTHON").unwrap_or_else(|_| "python".to_string());
    let mut command = Command::new(python);
    command.arg("-m").arg("aop.app_runtime").arg(action);

    if let Some(value) = project_id {
        if !value.trim().is_empty() {
            command.arg("--project-id").arg(value);
        }
    }
    if let Some(value) = run_id {
        if !value.trim().is_empty() {
            command.arg("--run-id").arg(value);
        }
    }
    if let Some(value) = job_id {
        if !value.trim().is_empty() {
            command.arg("--job-id").arg(value);
        }
    }
    if let Some(value) = limit {
        command.arg("--limit").arg(value.to_string());
    }
    if let Some(value) = dry_run {
        if value {
            command.arg("--dry-run");
        }
    }
    if let Some(value) = global_enabled {
        if value {
            command.arg("--global-enabled");
        }
    }
    if let Some(value) = project_enabled {
        if value {
            command.arg("--project-enabled");
        }
    }
    if let Some(value) = backend {
        if !value.trim().is_empty() {
            command.arg("--backend").arg(value);
        }
    }
    if let Some(value) = search_top_k {
        command.arg("--search-top-k").arg(value.to_string());
    }
    if let Some(value) = search_threshold {
        command.arg("--search-threshold").arg(value.to_string());
    }
    if let Some(value) = provider_id {
        if !value.trim().is_empty() {
            command.arg("--provider-id").arg(value);
        }
    }
    if let Some(value) = env_values {
        command.arg("--env-values-json").arg(value.to_string());
    }
    if let Some(value) = preferred {
        if value {
            command.arg("--preferred");
        }
    }
    if let Some(value) = prompt {
        if !value.trim().is_empty() {
            command.arg("--prompt").arg(value);
        }
    }
    if let Some(value) = project_name {
        if !value.trim().is_empty() {
            command.arg("--project-name").arg(value);
        }
    }
    if let Some(value) = project_path {
        if !value.trim().is_empty() {
            command.arg("--project-path").arg(value);
        }
    }
    if let Some(value) = primary_agent {
        if !value.trim().is_empty() {
            command.arg("--primary-agent").arg(value);
        }
    }

    let output = command.output().map_err(|error| format!("failed to spawn runtime bridge: {error}"))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if stderr.is_empty() {
            format!("runtime bridge exited with status {}", output.status)
        } else {
            stderr
        });
    }

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![app_runtime])
        .run(tauri::generate_context!())
        .expect("error while running AOP Desktop");
}
