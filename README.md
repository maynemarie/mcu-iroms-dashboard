# MCU IRO Dashboard — Streamlit + Supabase Edition

Interactive web dashboard for the **Manila Central University Institutional Research
Office**, built with Streamlit and backed by a Supabase Postgres database for permanent
data persistence.

## Stack

| Layer | Tech | Cost |
|---|---|---|
| Frontend / app | **Streamlit** | Free |
| Hosting | **Streamlit Community Cloud** | Free |
| Database | **Supabase Postgres** | Free tier (500 MB, 50k monthly active users) |
| Charts | **Plotly** | Free |
| Auth (future) | **Supabase Auth** with MCU-email allowlist | Free |

**Total monthly cost for prototype/internal use: $0.**

---

## One-time setup (15 minutes)

### A. Supabase project

1. Go to [supabase.com](https://supabase.com) → sign up (free, no credit card)
2. **New project** → pick a name (e.g., `mcu-iro`), set a strong DB password, region: Singapore (closest to Manila)
3. Wait ~2 minutes for the project to provision
4. Go to **SQL Editor** → **New query**
5. Open `schema.sql` from this repo → copy-paste into the editor → click **Run**
   - This creates 4 tables (erb_protocols, grant_projects, grant_reports, budget_entries) and helper views
6. Go to **Settings → API**
   - Copy **Project URL** (looks like `https://xxxx.supabase.co`)
   - Copy **anon public key** (long `eyJ...` string)

### B. Local development

```bash
cd mcu_iro_streamlit
pip install -r requirements.txt

# Create secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml and paste your Supabase URL and key

streamlit run app.py
```

Open `http://localhost:8501`. The sidebar should show **"✅ Database connected"**.

Try submitting an ERB protocol. Then visit your Supabase dashboard → **Table Editor → erb_protocols** to see the row.

### C. Deploy to Streamlit Cloud

1. Push the repo to GitHub:
   ```bash
   git init
   git add app.py requirements.txt schema.sql README.md .gitignore .streamlit/secrets.toml.example
   git commit -m "MCU IRO dashboard with Supabase"
   git remote add origin https://github.com/YOUR-USERNAME/mcu-iro-dashboard.git
   git branch -M main
   git push -u origin main
   ```

2. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub → **New app**
3. Pick your repo, branch `main`, main file `app.py`
4. Click **Advanced settings → Secrets** and paste:
   ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "eyJ...your-anon-key..."
   ```
5. Click **Deploy**

After ~2 minutes you get a public URL like `mcu-iro.streamlit.app`. Every submission persists to your Supabase Postgres — survives redeploys, browser refreshes, multiple users.

---

## Features

### Read-only pages
- **Overview** — KPI tiles (Faculty/Students donut, Scopus quartile donut, Grants by college, ERB status donut), live counts banner, Scopus 6-year trend, contributing colleges, IRB metrics, fee schedule
- **ERB Protocols (view)** — Live log of all submitted protocols
- **In-House Grants (view)** — Active grants metrics + recent project submissions + recent budget entries

### Write pages
- **Submit ERB Protocol** — Auto-generates `MCU-IRB-2026-XXXX` ID; full ethics checklist; persists to `erb_protocols` table
- **Submit Grant Project** — Auto-generates `MCU-IHG-2026-XXXX` ID; persists to `grant_projects`
- **Submit Grant Report** — Progress/final report against an existing grant ID
- **Log Budget Expense** — Category-coded budget entry with voucher/payee tracking

All write forms validate required fields and show success/error toast on submission.

---

## File structure

```
mcu_iro_streamlit/
├── app.py                              # The dashboard (Streamlit + Supabase)
├── requirements.txt                    # streamlit, plotly, pandas, supabase
├── schema.sql                          # Run once in Supabase SQL Editor
├── README.md                           # This file
├── .gitignore                          # Don't push secrets to GitHub
└── .streamlit/
    └── secrets.toml.example            # Template for local secrets
    └── secrets.toml                    # YOUR SECRETS — git-ignored, never push
```

---

## Database schema (4 tables)

| Table | Purpose | Key Column |
|---|---|---|
| `erb_protocols` | ERB / IRB protocol submissions | `protocol_id` (e.g., MCU-IRB-2026-0248) |
| `grant_projects` | In-house grant project proposals | `project_id` (e.g., MCU-IHG-2026-0039) |
| `grant_reports` | Progress / final reports on grants | `grant_id` (FK reference) |
| `budget_entries` | Expense logging per grant | `grant_id` (FK reference) |

Plus 3 analytics views (`v_erb_summary`, `v_grants_by_college`, `v_budget_by_category`) you can use later if you want to build a dedicated analytics page.

---

## Adding authentication (when ready)

Right now the dashboard is public — anyone with the URL can submit. To restrict to MCU email accounts:

### Option 1 — Supabase Auth (recommended)
1. Supabase Dashboard → **Authentication → Providers → Email** → enable
2. Update `schema.sql` to enable RLS:
   ```sql
   alter table erb_protocols enable row level security;
   create policy "mcu_email_only" on erb_protocols
     for insert with check (auth.email() like '%@mcu.edu.ph');
   ```
3. Add login UI in `app.py` (see [Streamlit + Supabase auth example](https://supabase.com/docs/guides/auth/server-side/creating-a-client))

### Option 2 — Streamlit native auth
- Streamlit 1.42+ has built-in auth via `st.user`. Simpler but less flexible than Supabase Auth.

### Option 3 — Microsoft Entra / Azure AD
- If MCU uses Microsoft 365, you can route logins through Entra ID for true SSO. This is the cleanest long-term option but takes coordination with MCU IT.

---

## Upgrading to MCU institutional hosting (production)

Eventually the dashboard should move from Streamlit Cloud to MCU's own servers for full data sovereignty:

1. **Database** — Migrate Supabase Postgres to MCU IT–hosted Postgres, or keep Supabase self-hosted on MCU infra
2. **Hosting** — Run Streamlit behind nginx on an MCU VM, or use Docker + MCU's Kubernetes (if available)
3. **Auth** — Route through MCU's Entra ID / Microsoft 365 SSO
4. **Domain** — Move from `*.streamlit.app` to `iro.mcu.edu.ph`
5. **Backups** — Schedule nightly Postgres dumps to MCU's backup infrastructure
6. **Privacy** — File DPA compliance documentation for any PII (ERB participant info, grant PI details)

Estimated MCU IT effort: 2–4 days. No change needed to the Python code.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Sidebar says "⚠️ Supabase not configured" | Check `.streamlit/secrets.toml` exists locally, or that secrets are set in Streamlit Cloud |
| "Database insert error: relation does not exist" | Run `schema.sql` in Supabase SQL Editor |
| Forms submit but data doesn't show up in DB | Check Supabase → Logs for RLS-related rejections |
| App times out / sleeps on free tier | Visit the URL to wake it; consider upgrading or moving to MCU hosting |
| Tables show old/stale data | Click the "Rerun" button in the top right (Streamlit caches resource by default) |

---

## What this version doesn't include yet (and roadmap)

- ❌ Authentication / login — add Supabase Auth (Section above)
- ❌ File uploads to Supabase Storage — currently only filenames are captured; integrate `sb.storage` to actually persist files
- ❌ Email notifications on new submissions — add a Supabase Edge Function or webhook → Resend/SendGrid
- ❌ Admin pages for ERB Secretariat / Research Office to approve/decline submissions — add status-update UI
- ❌ CSV/Excel exports of submission data — add `st.download_button` with `pd.to_csv`
- ❌ MCU logo in sidebar — replace placeholder
- ❌ Real production data — currently shows illustrative figures matching the HTML prototype

These are all 1-day additions when you're ready. Prioritise based on what the IRO team actually needs first.
