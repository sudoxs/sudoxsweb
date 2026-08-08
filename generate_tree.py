#!/usr/bin/env python3
"""
generate_tree.py — Interactive tree.json builder for SUDOXS Archive

Usage:
    python3 generate_tree.py

Scans current directory, lets you pick folders to include in the archive.
Saves your selection so next time it remembers.
"""
import os
import json
import sys

# Items to ignore
IGNORE = {
    '.git', 'node_modules', '.github', '__pycache__', '.venv', 'venv',
    'tree.json', 'generate_tree.py', '.gitignore', '.nojekyll',
    '.sx_config.json'
}

def get_folders(path="."):
    """Get all subdirectories in path."""
    folders = []
    try:
        for entry in sorted(os.listdir(path)):
            full = os.path.join(path, entry)
            if os.path.isdir(full) and entry not in IGNORE:
                folders.append(entry)
    except Exception:
        pass
    return folders

def scan_directory(path):
    """Recursively build tree node for a directory."""
    name = os.path.basename(path)
    rel = os.path.relpath(path, ".").replace("\\", "/")
    node = {
        "name": name,
        "type": "dir",
        "path": rel,
        "children": []
    }
    try:
        entries = sorted(os.listdir(path))
    except Exception:
        entries = []
    for entry in entries:
        if entry in IGNORE:
            continue
        entry_path = os.path.join(path, entry)
        entry_rel = os.path.relpath(entry_path, ".").replace("\\", "/")
        if os.path.isdir(entry_path):
            node["children"].append(scan_directory(entry_path))
        else:
            node["children"].append({
                "name": entry,
                "type": "file",
                "path": entry_rel,
                "download_url": entry_rel
            })
    return node

def load_config():
    """Load previously selected folders."""
    config_file = ".sx_config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(selected):
    """Save selected folders."""
    with open(".sx_config.json", "w", encoding="utf-8") as f:
        json.dump({"selected_folders": selected}, f, indent=2, ensure_ascii=False)

def interactive_select(folders):
    """Let user pick folders interactively."""
    print("\n" + "=" * 56)
    print("  SUDOXS ARCHIVE — Interactive Folder Scanner")
    print("=" * 56)
    print("\n  Found folders in current directory:\n")
    for i, f in enumerate(folders, 1):
        print(f"    [{i}] {f}")
    print(f"\n    [0] Select ALL folders")
    print(f"    [s] Skip / keep previous selection")
    print("\n  Enter numbers separated by commas (e.g. 1,3,4)")
    print("  Or type 'all' to select everything, 'q' to quit")

    choice = input("\n  > ").strip().lower()

    if choice == 'q':
        sys.exit(0)
    if choice in ('s', ''):
        return None  # Signal to use previous
    if choice in ('0', 'all'):
        return folders

    selected = []
    try:
        indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
        for idx in indices:
            if 1 <= idx <= len(folders):
                selected.append(folders[idx - 1])
    except ValueError:
        print("  Invalid input. Using all folders.")
        return folders

    return selected

def main():
    folders = get_folders()
    if not folders:
        print("\n  No folders found in current directory.")
        print("  Create some folders and put your .md files inside them.")
        sys.exit(1)

    config = load_config()
    selected = None

    if config.get("selected_folders"):
        prev = config["selected_folders"]
        print(f"\n  Previous selection: {prev}")
        ans = input("  Use previous? [Y/n/new] ").strip().lower()
        if ans == 'n':
            selected = interactive_select(folders)
        elif ans == 'new':
            selected = interactive_select(folders)
        else:
            selected = prev
    else:
        selected = interactive_select(folders)

    if selected is None:
        selected = config.get("selected_folders", folders)

    if not selected:
        print("  No folders selected. Exiting.")
        sys.exit(0)

    save_config(selected)

    print(f"\n  Building tree.json for: {selected}\n")
    tree = []
    for folder in selected:
        if os.path.isdir(folder):
            tree.append(scan_directory(folder))
        else:
            print(f"  Warning: '{folder}' not found, skipping.")

    with open("tree.json", "w", encoding="utf-8") as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)

    # Stats
    md_count = 0
    folder_count = 0
    def count_stats(node):
        nonlocal md_count, folder_count
        if node.get("type") == "file" and node["name"].endswith(".md"):
            md_count += 1
        if node.get("type") == "dir":
            folder_count += 1
        for child in node.get("children", []):
            count_stats(child)

    for node in tree:
        count_stats(node)

    print("  " + "-" * 40)
    print(f"  tree.json generated successfully!")
    print(f"    Top folders  : {len(tree)}")
    print(f"    Sub-folders  : {folder_count - len(tree)}")
    print(f"    Total .md    : {md_count}")
    print("  " + "-" * 40)
    print("\n  Next steps:")
    print("    git add tree.json")
    print("    git commit -m 'update archive'")
    print("    git push origin main")

if __name__ == "__main__":
    main()
