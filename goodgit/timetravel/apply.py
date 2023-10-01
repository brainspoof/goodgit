import os
import tempfile
import git
import questionary
import re
import subprocess
from rich import print

from .timetravel import read_from_file

def slugify(text):
    """Slugify a text string."""
    return re.sub(r'[\W_]+', '_', text)

def apply_timetravel():
    """Apply time-traveled changes to the current branch."""
    # Initialize temp dir and config file
    temp_dir = tempfile.gettempdir()
    config_file = os.path.join(temp_dir, 'goodgit_time_travel_config.conf')

    # Initialize GitPython repo object
    repo = git.Repo(os.getcwd())

    # Check if HEAD is detached
    is_detached = repo.head.is_detached

    if is_detached:
        current_branch = read_from_file(config_file)
        commit = next(repo.iter_commits())
        commit_hex = commit.hexsha
        commit_message = commit.message.strip()
        
        should_proceed = questionary.confirm(f"Do you want bring the commit with message: '{commit_message}' to the present?", default=False).ask()
        if not should_proceed:
            print("[red]Time travel cancelled.[/red]")
            exit()

        new_branch_name = f'timetravelled_from_{slugify(commit_message)}_{commit_hex[:7]}'
        repo.git.branch(new_branch_name, commit_hex)
        repo.git.checkout(current_branch)

        latest_commit_message = next(repo.iter_commits()).message.strip()
        if latest_commit_message == 'LATEST_CODE_STATE':
            repo.git.reset('HEAD~1')

            if repo.is_dirty():
                repo.git.add('-A')
                repo.git.commit('-m', f'CODE BEFORE TIME TRAVELLING TO "{commit_message}"')

        previous_git_merge_autoedit = os.environ.get('GIT_MERGE_AUTOEDIT', None)
        os.environ['GIT_MERGE_AUTOEDIT'] = 'no'

        subprocess.run(['git', 'checkout', new_branch_name])
        subprocess.run(['git', 'merge', '-s', 'ours', current_branch, '-m', f"TIME TRAVELLED TO '{commit_message}' ({commit_hex[:7]})"])
        subprocess.run(['git', 'checkout', current_branch])
        subprocess.run(['git', 'merge', new_branch_name])

        if previous_git_merge_autoedit is not None:
            os.environ['GIT_MERGE_AUTOEDIT'] = previous_git_merge_autoedit
        elif 'GIT_MERGE_AUTOEDIT' in os.environ:
            del os.environ['GIT_MERGE_AUTOEDIT']

        repo.git.branch('-D', new_branch_name)

        print("[green]Time travel complete! The old commit state is now the latest commit.[/green]")
    else:
        print("[yellow]You're already on the latest commit. No need to time travel![/yellow]")

