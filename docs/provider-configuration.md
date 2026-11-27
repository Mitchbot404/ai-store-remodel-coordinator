# Local Windows provider configuration

The prototype runs locally from the Windows repository. `.streamlit/config.toml` binds Streamlit to `127.0.0.1`; GitHub hosts source and CI, not the running application. No cloud deployment is configured. The Phase 6A preparation check found no listeners on local ports 8501–8505. This describes that check, not a permanent service status.

## Secure key entry

For the approved 27-trial experiment use the [dedicated evaluation launcher](live-evaluation.md). The Streamlit instructions below are for offline prototype sessions only.

Use your own local PowerShell terminal. Do not paste a key into chat, source files, Git commands, command arguments, screenshots, or GitHub Actions secrets for this exercise. The repository is in OneDrive, so do not save the key in a local `.env` file there either.

1. Follow README setup to create the project's `.venv` and install requirements if necessary.
2. From the repository directory run:

   ```powershell
   .\scripts\Start-Local.ps1 -LoadApiKey
   ```

3. Enter the restricted project key at the hidden prompt. The prompt does not echo the key or put it in shell command history. The script places it in the current process's `OPENAI_API_KEY`, inherited by the Streamlit child process, and removes it when the app exits. No file or persistent user environment variable is created. You can supply `-PythonExe` with an existing compatible Python executable if needed.
4. The script announces only that a key was loaded. It deliberately keeps live calls disabled and selects `mock_bounded` while reference review is pending. Omit `-LoadApiKey` to run entirely offline without a key.

Do not weaken machine execution policy to run the script; if your organization blocks scripts, follow its local administration process. A process environment is not an encrypted secret store: the running process and a sufficiently privileged local administrator can inspect it. Use only your dedicated restricted key, and revoke it if exposed. This launcher is a preparation path; a later evaluation process will need the key entered again privately.

## Provider contract and enablement

The new `OpenAIProvider` sends only whitelisted synthetic case information to `https://api.openai.com/v1/responses`. Its model is pinned to `gpt-5.4-mini-2026-03-17`; reasoning effort is `none`, maximum output is 1,500 tokens, storage is disabled, and no tools are supplied. HTTP redirects and automatic retries are disabled. The original canonical mock remains the default. `CANDIDATE_PROVIDER=mock_bounded` selects the new deterministic analysis control; `openai` selects the Responses adapter.

Live calls fail closed unless `OPENAI_LIVE_ENABLED=yes`, `PHASE6A_REFERENCE_APPROVED=yes`, and `OPENAI_API_KEY` are configured in the calling process. Do not enable these before the owner reviews [reference expectations](reference-expectations.md). The evaluation CLI additionally requires the exact reviewed dataset SHA256 via `--approval-hash`. These are explicit local approval attestations, not a separate enterprise authorization system. Supervisor permissions still guard generation from the application.

The project owner has approved synthetic-only transmission and a **$2 total evaluation budget**. The reported provider setup is a dedicated project with $5 credit, a $2 monthly limit, 50%/90% alerts, no auto-reload, GPT-5.4 mini only, and Responses API Write permission. This account configuration is user-reported; no key, balance or provider dashboard has been inspected by the implementation.

The adapter reserves conservative maximum request cost before any network request, atomically across processes. Its cumulative ledger is `%LOCALAPPDATA%\CEN4010-Remodel-Coordinator\evaluation-budget.sqlite3`, outside OneDrive and the repository. All failures retain their reservation because billing may be uncertain. Limits are $2 cumulative and 30 attempts, with a 32 KiB request cap and 1,500-output-token cap; there is no reset API. Do not delete the ledger, switch Windows users, or make unrelated requests against this budget. These local controls cannot account for outside use of the key. They supplement the provider controls rather than relying on alerts as a hard cap.

## Price, privacy and evidence

At the verified standard rates of $0.75 per million input tokens and $4.50 per million output tokens, an illustrative 3,000-input/1,000-output request costs $0.00675; 27 such calls cost about $0.18. Actual usage differs. The conservative reservation includes the full serialized request byte count plus an overhead allowance, not just the short user note. No charges have been incurred by this preparation work. [Official model and pricing reference](https://developers.openai.com/api/docs/models/gpt-5.4-mini).

`store=false` does not guarantee zero retention. API data is not used for training by default, but abuse-monitoring retention may apply. Only synthetic evaluation records are authorized; never transmit the Solution Design Report's personal/employer observations as evaluation input. [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).

Structured output constrains syntax, not semantic factuality or usefulness. Refusals, incomplete responses and business-rule violations still need handling. [Structured output documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

Run 02 confirmed access to the pinned model for one completed response. The application rejected its repeated evidence ID. Offline test transports remain separate from live evaluation evidence. [Observed result](evaluation-results.md)
