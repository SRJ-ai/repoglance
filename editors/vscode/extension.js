// Minimal VS Code extension: runs `repoglance --json` on the workspace and
// surfaces complexity hotspots as diagnostics in the Problems panel.
const vscode = require("vscode");
const cp = require("child_process");
const path = require("path");

function activate(context) {
  const collection = vscode.languages.createDiagnosticCollection("repoglance");
  context.subscriptions.push(collection);

  const cmd = vscode.commands.registerCommand("repoglance.analyze", () => {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
      vscode.window.showWarningMessage("repoglance: no workspace folder open.");
      return;
    }
    const root = folders[0].uri.fsPath;
    const exe = vscode.workspace.getConfiguration("repoglance").get("path", "repoglance");

    cp.execFile(exe, [root, "--json", "--no-git"], { maxBuffer: 20 * 1024 * 1024 }, (err, stdout) => {
      if (err) {
        vscode.window.showErrorMessage("repoglance failed: " + err.message);
        return;
      }
      let report;
      try {
        report = JSON.parse(stdout);
      } catch (e) {
        vscode.window.showErrorMessage("repoglance: could not parse output.");
        return;
      }
      const byFile = new Map();
      for (const h of report.hotspots || []) {
        if (h.complexity < 10) continue;
        const uri = vscode.Uri.file(path.join(root, h.path));
        const line = Math.max(0, (h.line || 1) - 1);
        const range = new vscode.Range(line, 0, line, 200);
        const sev = h.complexity >= 25
          ? vscode.DiagnosticSeverity.Error
          : vscode.DiagnosticSeverity.Warning;
        const diag = new vscode.Diagnostic(
          range,
          `Function '${h.name}' has cyclomatic complexity ${h.complexity}.`,
          sev
        );
        diag.source = "repoglance";
        if (!byFile.has(uri.fsPath)) byFile.set(uri.fsPath, { uri, list: [] });
        byFile.get(uri.fsPath).list.push(diag);
      }
      collection.clear();
      for (const { uri, list } of byFile.values()) collection.set(uri, list);
      vscode.window.showInformationMessage(
        `repoglance: health ${report.health.score}/100 (${report.health.grade}).`
      );
    });
  });

  context.subscriptions.push(cmd);
}

function deactivate() {}

module.exports = { activate, deactivate };
