As a non-developer trying to build an application and learning developer tools and workflows at the same time, I have made many mistakes with this project. I did not know how to set up tools and environments. I did not know how to use the tools correctly or understand instructions on how to use them. I did not know how to interpret errors or respond to them. I was not clear on the app requirements nor the patterns of development to follow. As a result, progress on development has been slow and the current organization of the project impedes proper workflows and the production of quality code. 

Environment and tooling: 

Windows 11
VS Code
Cursor
spec-kitty (https://github.com/Priivacy-ai/spec-kitty/blob/main/README.md)
Git Bash
Git for Windows
GitHub
Claude Code
Claude Desktop
Gemini CLI
ChatGPT

Multiple Windows development environment and tooling configuration issues have been addressed to resolve errors that were impeding workflows. 
- PowerShell 7 is now installed so the pwsh command called by scripts works.
- ~.\bashrc is configured properly so it can execute the commands required by scripts
- PATH settings for python are properly configured
- A spec-kitty Powershell script is repaired to function as intended. 

However, some mistakes I made have put the project in an untenable state: 

- I did not understand the location at which spec-kitty needed to be installed. I installed it at C:\Users\Kent\Vault-repos that has these subdirectories: 

	.claude
	bake-tracker
	bug-driven-development
	google-apps-script-libraries
	intentional
	kg-automation
	metalbox
	multi-habit-tracker
	rk-comp-wksp

It should be installed in each repo it will be used in, or bake-tracker, in this particular case. I have not noticed any serious side effects but I'm documenting the mistake in case it matters at some point. 

- I did not understand that spec-kitty commands needed to be run from the root of the repo in which it is to be operating. For a long time I was using Claude Code to perform what I thought were spec-kitty workflows however since the actual commands were not working it was instead reading the scripts and attempting to manually perform the workflow actions which meant many intended actions were truncated, skipped, or performed incorrectly. 
- A significant amount of specification, planning, and implementation work had been completed.

- I further did not understand that Claude Code was meant to be run and operated in a given feature worktree root created by spec-kitty. None of the work was performed this way. 

The result of these mistakes meant that the project was improperly planned and organized. 

- Some features were created and they appeared to go through the normal spec-kitty workflow but I didn't know enough at the time to know if this is in fact the case, or if claude code was doing its best to follow the workflow manually. 
- Along the way, there was a failure to create a worktree and it fell back to creating a feature branch of the repo and some of the work was completed in that manner. 
- The result of all this confusion is there are missing worktrees, possibly missing code, possibly missing specifications, somewhat duplicate worktrees, and no clear path forward.

The worktree structure currently looks like this: 

002-service-layer-for
d----          11/14/2025  4:22 PM                004-finishedunit
d----          11/15/2025 11:50 PM                004-finishedunit-model-refactoring
d----          11/14/2025  1:35 PM                004-productionrun
d----          11/16/2025 12:58 AM                005-database-schema-foundation

There should only be one "004" feature if my understanding is correct. 

- As some of the design flaws started to come to light through testing versions of the app it became clear some serious refactoring was required. This work began to take place in worktree `004-finishedunit-model-refactoring`. By this point I was starting to use spec-kitty properly, however, a large number of changes, each of which were feature-size in scope, got planned as a series of about 11-15 work packages within `004-finishedunit-model-refactoring` 
- After some of this work was completed it started to become clear that the scope of work required to complete these work packages really deserved the full spec-kitty workflow cycle individually. This is so the code could be merged to main after each addition and built on by subsequent packages and not built as one giant feature. 
- Additionally, as some work packages were completed it became evident that database schema elements were missing. It wasn't clear if minor or structural changes were needed. Upon further inspection evidence of the work completed at the schema layer could not be found. I began to lose confidence that we were building on a solid foundation.  
- It became clear that the work required to complete `004-finishedunit-model-refactoring` may need significant schema changes so now being armed with a proper understanding of the tooling and workflow I initiated a new feature build following the correct procedures and workflow in spec-kitty to create worktree `005-database-schema-foundation`.

This is where the project stands. 

What I want is your help restructuring the project so it is properly organized, specified, planned, and implemented while preserving as much design and implementation work as can be reused from the current structure and code. The goal is to start or restart as needed to ensure there is a solid foundation on which all features may be built and and tested. I want to clean up all the spec-kitty artifacts without losing anything of value so the project can proceed with higher velocity and greater quality. 

Note that we can utilize Claude Code, Cursor, and Gemini CLI as agents for parallel development and code reviews. Claude Desktop, ChatGPT, and Gemini as are available as desktop app resources. 

Provide your assessment of the situation and draft a plan. 