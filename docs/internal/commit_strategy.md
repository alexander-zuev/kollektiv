# Commit Management Guide

## Commit Structure
Use the Conventional Commits format:
`<type>[optional scope]: <description>`

Types: feat, fix, docs, style, refactor, test, chore

Example:
```bash
feat(crawler): implement async crawl for multiple URLs

Add async_crawl_url method to FireCrawler
Update app.py to use new async crawling feature
Add error handling for failed crawl jobs
```

## Logically Grouping Commits

Group related changes into single, meaningful commits:

1. Feature Implementation:
   - Basic functionality
   - Tests
   - Error handling
   - Documentation updates

2. Bug Fix:
   - Fix implementation
   - Test updates
   - Documentation adjustments

3. Refactoring:
   - Code restructuring
   - Test updates
   - Documentation changes

## Managing and Combining Commits

### When to Combine Commits:
- Before merging a feature branch into main
- When preparing for a release
- After completing a logical unit of work with multiple interim commits

### How to Combine Commits:
Use interactive rebase:

1. Ensure you're on your feature branch
2. Run: `git rebase -i HEAD~n` (where n is the number of commits to review)
3. In the rebase todo list:
   - `pick` the first commit
   - `squash` or `fixup` subsequent related commits
   - `reword` to change commit messages

Example rebase todo:
```bash
pick abc1234 feat(crawler): initial async crawl implementation
squash def5678 Add error handling to async crawl
squash ghi9101 Update tests for async crawl
reword jkl1121 Update documentation for async crawl feature
```
4. Save and close the editor
5. Edit the combined commit message if prompted

### Updating Commit Messages:
- During rebase: Use `reword` for commits you want to update
- For the last commit: Use `git commit --amend`

## Best Practices
1. Commit often during development
2. Use feature branches for major changes
3. Rebase and combine commits before merging to main
4. Keep commit messages clear and descriptive
5. Reference issue numbers when applicable (e.g., "Fix #123: Handle timeout in async crawl")

Remember, these practices aim to create a clear project history. Adjust as needed for your workflow.