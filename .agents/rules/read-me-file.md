---
trigger: always_on
---

## README & Setup File Rules

Whenever any feature, API, workflow, configuration, dependency, or logic changes:

The agent MUST:
- Update `README.md` accordingly
- Update setup/install steps if required
- Update usage examples
- Add newly required environment variables to `.env.example`
- Update command examples if scripts change
- Update API examples if request/response changes
- Remove outdated documentation
- Keep documentation synchronized with the latest codebase

---

## Mandatory README Updates

The agent MUST update README when:
- A new feature is added
- Existing behavior changes
- New dependency is introduced
- New environment variable is added
- Setup process changes
- Build/deployment process changes
- API routes change
- CLI commands change
- Folder structure changes significantly

---

## Setup File Instructions

The agent MUST update related setup/config files when required:
- `requirements.txt`
- `package.json`
- `.env.example`
- `Dockerfile`
- `docker-compose.yml`
- CI/CD workflows
- startup scripts

---

## Environment Variable Rules

Whenever a new environment variable is introduced:
- Add it to `.env.example`
- Mention it in README
- Provide a short description
- Mark whether it is required or optional

---

## Accuracy Rules

The agent MUST ensure:
- README instructions work on a fresh setup
- Installation steps are complete
- Commands are copy-paste ready
- Examples reflect current implementation
- No outdated feature references remain

---

## Final Verification

Before completing changes, verify:
- [ ] README updated
- [ ] Setup/config files updated
- [ ] Examples updated
- [ ] Environment variables documented
- [ ] Old documentation removed
- [ ] Installation steps tested logically