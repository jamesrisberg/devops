# devops - Development Environment Topology Visualizer

A TUI (Terminal User Interface) application built with Textual that helps visualize and manage your development environment setup.

## Project Structure

```
src/devops/
├── __main__.py          # Entry point
├── app.py               # Main Textual App class
├── screens/
│   ├── main.py          # Main tabbed interface screen
│   └── ffmpeg.py        # FFmpeg screen
├── collectors/          # Data collectors for each environment type
│   ├── base.py          # BaseCollector and EnvEntry dataclass
│   ├── homebrew.py      # Homebrew packages
│   ├── homebrew_async.py # Async homebrew collection
│   ├── python_envs.py   # Python environments (conda, pyenv, venv)
│   ├── node.py          # Node.js versions (nvm, fnm, volta)
│   ├── ruby.py          # Ruby versions (rbenv, chruby)
│   ├── rust.py          # Rust toolchains
│   ├── npm.py           # NPM packages (global + local)
│   ├── path.py          # PATH entries
│   ├── shell_config.py  # Shell config files
│   ├── symlinks.py      # Symlink analysis
│   └── asdf.py          # asdf version manager
├── widgets/
│   ├── env_tree.py      # Tree widget for displaying entries
│   └── detail_panel.py  # Detail panel for selected items
├── cache/               # Caching for slow operations
│   ├── brew_cache.py
│   └── brew_list_cache.py
└── actions/
    └── shell_edit.py    # Shell config editing actions
```

## Key Design Decisions

### Tab Visibility
- Tabs only appear when there's meaningful data to show
- `is_available()` static methods use **fast filesystem checks only** - no subprocess calls
- Node tab: only shows if nvm/fnm/volta have actual versions installed, or Homebrew node exists
- Ruby tab: only shows for rbenv/chruby with versions - NOT for Homebrew/system Ruby (they don't manage environments)
- Rust tab: only shows if rustup is installed with toolchains
- asdf tab: only shows if asdf has plugins installed

### Data Loading
- Fast collectors (Shell, PATH, Symlinks) load synchronously on mount
- Slow collectors (Homebrew, Python, NPM) preload in background via `set_timer()` on mount
- Homebrew uses worker threads and caching for best UX

### EnvEntry Dataclass
All collectors return `list[EnvEntry]`. Required fields:
- `name: str` - Display name
- `path: str` - Path or identifier (required!)
- `status: Status` - HEALTHY, WARNING, or ERROR
- `details: dict` - Arbitrary metadata for the detail panel

## Dependencies

Core:
- `textual>=0.47.0` - TUI framework (currently using 7.2.0)
- `rich>=13.0.0` - Terminal formatting
- `pyperclip>=1.8.0` - Clipboard support

The Homebrew formula pins specific versions of all transitive dependencies.

## Development

```bash
# Run from source
cd ~/dev/devops/devops
python -m devops

# Run tests
pytest
```

## Releasing Updates

### 1. Make your changes and commit

```bash
cd ~/dev/devops/devops
git add -A
git commit -m "Description of changes"
git push
```

### 2. Update the v0.1.0 tag (or create new version)

```bash
# Delete and recreate tag at current commit
git tag -d v0.1.0
git tag v0.1.0
git push origin v0.1.0 --force
```

### 3. Rebuild and upload the release tarball

```bash
# Remove old tarball if exists
rm -f devops-0.1.0.tar.gz

# Delete old asset from GitHub release
gh release delete-asset v0.1.0 devops-0.1.0.tar.gz --yes

# Create new tarball
git archive --format=tar.gz --prefix=devops-0.1.0/ -o devops-0.1.0.tar.gz HEAD

# Upload to release
gh release upload v0.1.0 devops-0.1.0.tar.gz

# Get the new SHA256
shasum -a 256 devops-0.1.0.tar.gz
```

### 4. Update the Homebrew tap

```bash
cd ~/dev/homebrew-devops

# Update the sha256 in Formula/devops.rb with the new hash
# (replace OLD_HASH with the previous hash, NEW_HASH with the new one)
sed -i '' 's/OLD_HASH/NEW_HASH/' Formula/devops.rb

# Commit and push
git add -A
git commit -m "Update SHA256 for v0.1.0 - description of changes"
git push
```

### 5. Test the update

```bash
brew update
brew reinstall devops
devops
```

### One-liner for steps 2-4 (after committing)

```bash
cd ~/dev/devops/devops && \
git tag -d v0.1.0 && git tag v0.1.0 && git push origin v0.1.0 --force && \
rm -f devops-0.1.0.tar.gz && \
gh release delete-asset v0.1.0 devops-0.1.0.tar.gz --yes 2>/dev/null; \
git archive --format=tar.gz --prefix=devops-0.1.0/ -o devops-0.1.0.tar.gz HEAD && \
gh release upload v0.1.0 devops-0.1.0.tar.gz --clobber && \
NEW_SHA=$(shasum -a 256 devops-0.1.0.tar.gz | cut -d' ' -f1) && \
echo "New SHA: $NEW_SHA" && \
cd ~/dev/homebrew-devops && \
OLD_SHA=$(grep sha256 Formula/devops.rb | cut -d'"' -f2) && \
sed -i '' "s/$OLD_SHA/$NEW_SHA/" Formula/devops.rb && \
git add -A && git commit -m "Update SHA256 for v0.1.0" && git push
```

## Homebrew Formula Location

- Tap repo: `~/dev/homebrew-devops`
- Formula: `~/dev/homebrew-devops/Formula/devops.rb`
- GitHub: `https://github.com/jamesrisberg/homebrew-devops`

Users install with:
```bash
brew tap jamesrisberg/devops
brew install devops
```

Or in one command:
```bash
brew install jamesrisberg/devops/devops
```

## Common Issues

### "EnvEntry missing positional argument 'path'"
All EnvEntry objects require a `path` argument. Check the collector.

### Tab shows when it shouldn't
Check the `is_available()` method - it should only use fast filesystem checks and verify actual installations exist.

### Tab hangs when clicked
The collector's `collect()` method is running slow subprocess calls. Consider:
1. Moving slow checks out of `is_available()` 
2. Using background workers like Homebrew does
3. Adding caching

### Homebrew formula fails with wrong checksum
The tarball was rebuilt but the formula wasn't updated. Run the release process again.
