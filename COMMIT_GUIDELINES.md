# Commit Message Guidelines

These guidelines help maintain clear and consistent commit messages for better project history and collaboration.

## Commit Message Structure

Each commit message should follow this structure:

```
[TAG] component: describe your change in a short sentence (ideally < 50 chars)

Long version of the change description, including the rationale for the change,
or a summary of the feature being introduced.

Please spend a lot more time describing WHY the change is being done rather
than WHAT is being changed. This is usually easy to grasp by actually reading
the diff. WHAT should be explained only if there are technical choices
or decision involved. In that case explain WHY this decision was taken.

End the message with references, such as task or bug numbers, PR numbers, and
tickets, following the suggested format:
task-123 (related to task)
Fixes #123  (close related issue on Github)
Closes #123  (close related PR on Github)
ticket-123 (related to ticket)
```

## Tags

Tags are used to categorize commits. Use one of the following tags:

- **[FIX]** - Bugfixes: Mostly used in stable versions but also valid if you are fixing a recent bug in development version
- **[REF]** - Refactoring: When a feature is heavily rewritten
- **[ADD]** - Adding new modules
- **[REM]** - Removing resources: Removing dead code, removing views, removing modules, etc.
- **[REV]** - Reverting commits: If a commit causes issues or is not wanted, reverting it is done using this tag
- **[MOV]** - Moving files: Use `git mv` and do not change content of moved file otherwise Git may lose track and history of the file; also used when moving code from one file to another
- **[REL]** - Release commits: New major or minor stable versions
- **[IMP]** - Improvements: Most of the changes done in development version are incremental improvements not related to another tag
- **[MERGE]** - Merge commits: Used in forward port of bug fixes but also as main commit for feature involving several separated commits
- **[CLA]** - Signing the Individual Contributor License
- **[I18N]** - Changes in translation files
- **[PERF]** - Performance patches
- **[CLN]** - Code cleanup
- **[LINT]** - Linting passes

## Component Name

After the tag comes the modified component or feature name. Use the technical name as functional name may change with time. If several components are modified, list them or use "various" to tell it is cross-components. Unless really required or easier, avoid modifying code across several components in the same commit. Understanding component history may become difficult.

## Commit Message Header

After tag and component name comes a meaningful commit message header. It should be self-explanatory and include the reason behind the change. Do not use single words like "bugfix" or "improvements". Try to limit the header length to about 50 characters for readability.

Commit message header should make a valid sentence once concatenated with `if applied, this commit will <header>`. For example `[IMP] image_processing: improve error handling for invalid file formats` is correct as it makes a valid sentence `if applied, this commit will improve error handling...`.

## Commit Message Full Description

In the message description specify the part of the code impacted by your changes (component name, library, transversal object, etc.) and a description of the changes.

**First explain WHY you are modifying code.** What is important if someone goes back to your commit in about 4 decades (or 3 days) is why you did it. It is the purpose of the change.

What you did can be found in the commit itself. If there was some technical choices involved it is a good idea to explain it also in the commit message after the why.

Please avoid commits which simultaneously impact multiple components. Try to split into different commits where impacted components are different. It will be helpful if we need to revert changes in a given component separately.

Don't hesitate to be a bit verbose. Most people will only see your commit message and judge everything you did in your life just based on those few sentences. No pressure at all.

**You spend several hours, days or weeks working on meaningful features. Take some time to calm down and write clear and understandable commit messages.**

## Examples

### Example 1: Refactoring
```
[REF] image_processing: use optimized algorithm for batch processing

This replaces the former sequential processing with a more efficient
parallel approach that significantly reduces processing time for large
image sets.

Closes #123
Fixes #124
```

### Example 2: Bugfix
```
[FIX] file_handler: correct encoding issue with special characters

The file handler was not properly handling UTF-8 encoded files with
special characters, causing data corruption in certain cases.

Closes #125
Fixes #126
```

### Example 3: Bugfix with Technical Explanation
```
[FIX] ui: remove unused container div, fixes layout rendering issue

The CSS layout depends on the main container element
being the first/last child of its parent.
This was not the case because of the invisible
and unused container div.
```

## Important Note

Use the long description to explain the **WHY** not the **WHAT**, the **WHAT** can be seen in the diff.

## Git Configuration

Be sure to define both `user.email` and `user.name` in your local git config:

```bash
git config --global user.email <your-email>
git config --global user.name <your-name>
```

## Git Hook Setup (Automatic Validation)

This repository includes a `commit-msg` hook that automatically validates commit messages against these guidelines. The hook will **block commits** that don't follow the required format.

### Quick Setup

The hook is already included in `.git/hooks/commit-msg`. If it's not working, ensure:

1. **The hook file exists and is executable:**
   ```bash
   ls -la .git/hooks/commit-msg
   ```

2. **On Windows (Git Bash):** The hook should work automatically. If you encounter issues, you can test it manually:
   ```bash
   python .git/hooks/commit-msg <path-to-commit-message-file>
   ```

3. **On Linux/Mac:** Make sure the hook is executable:
   ```bash
   chmod +x .git/hooks/commit-msg
   ```

### What the Hook Validates

- ✅ Format: `[TAG] component: description`
- ✅ Valid tags (FIX, REF, ADD, REM, REV, MOV, REL, IMP, MERGE, CLA, I18N, PERF, CLN, LINT)
- ✅ Header length (max 50 characters)
- ⚠️ Warns if longer description is missing (doesn't block)

### Testing the Hook

You can test the hook manually:

```bash
# Create a test commit message file
echo "docs: test message" > test_msg.txt

# Test with invalid format (should fail)
python .git/hooks/commit-msg test_msg.txt

# Test with valid format (should pass)
echo "[IMP] documentation: add test documentation" > test_msg.txt
python .git/hooks/commit-msg test_msg.txt
```

### Troubleshooting

**Quick Fix for Windows Users:**
If you're on Windows and get Python errors when committing, you can use:
```bash
git commit --no-verify -m "[TAG] component: your message"
```
This bypasses the hook validation. Just make sure your commit message follows the format: `[TAG] component: description`. See "Bypassing the Hook" section below for details.

**Problem:** Hook doesn't run automatically
- **Solution:** Ensure Git is using the hooks directory: `git config core.hooksPath .git/hooks`

**Problem:** Python not found error on Windows
- **Solution:** The hook may use `python3` by default, but on Windows the command is typically `python`. If you encounter "Python wurde nicht gefunden" errors, you can:
  1. Use `git commit --no-verify` to bypass the hook (see below)
  2. Or modify the hook's shebang line to use `python` instead of `python3`
  
  **Note:** On this Windows system, it's acceptable to use `--no-verify` for commits as long as the commit message format follows these guidelines. The hook validation is primarily for automated checks, and manual adherence to the format is sufficient.

**Problem:** Hook blocks valid commits
- **Solution:** Check the error message - it will tell you what's wrong. Common issues:
  - Missing tag brackets: Use `[IMP]` not `IMP`
  - Missing colon: Use `component: description` format
  - Invalid tag: Check the list of valid tags above
  - Header too long: Keep it under 50 characters

### Bypassing the Hook

If you need to bypass the hook (e.g., for emergency fixes or when the hook has Python path issues on Windows), use:

```bash
git commit --no-verify -m "[TAG] component: message"
```

**Windows Note:** On Windows systems where the hook fails due to Python path issues (`python3` vs `python`), using `--no-verify` is acceptable as long as you manually ensure your commit messages follow the required format. The hook is primarily for automated validation, and manual adherence to these guidelines is sufficient.

**General Warning:** Only use `--no-verify` when necessary. Always ensure your commit messages follow the format guidelines even when bypassing the hook.