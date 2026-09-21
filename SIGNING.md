# Code signing policy — preparation, not yet approved

Capcraft 1.2 (v1.2.0) is currently **unsigned**. No SignPath application has been
submitted by this change, no subscription/certificate has been approved, and no
signed release is available. Do not describe existing downloads as signed.

## Proposed provider and responsibilities

Proposed provider: SignPath Foundation's open-source program. Acceptance is not
guaranteed, particularly for a newly released executable project. Its certificate
identifies SignPath Foundation, not JBH, as the certificate publisher.

Proposed author, reviewer and signing approver: JBH
([myflair77](https://github.com/myflair77)). The maintainer must confirm these roles
and enable MFA on GitHub and SignPath personally. Do not share passwords, recovery
codes, private keys or API tokens in chat or source control.

## Application draft (maintainer must review and submit)

- Project: Capcraft
- Repository: https://github.com/myflair77/Capcraft
- Homepage: https://capcraft-zeta.vercel.app/
- Existing release: https://github.com/myflair77/Capcraft/releases/tag/v1.2.0
- License: GPL-3.0-only for original application code; third-party components retain their licenses.
- Public contact: myflair77@gmail.com
- Description: Capcraft is a Windows screen-capture and annotation application.
  It supports drawing, shapes, arrows, magnified popouts, Gaussian blur, image
  editing and local multilingual OCR. It is built with Python, PyQt6/Qt WebEngine,
  Fabric.js and local ONNX OCR models.
- Intended signing scope: our packaged application executable and Inno Setup
  installer. Upstream DLLs and tools must not be re-signed as our own code.
- Build system: GitHub Actions on GitHub-hosted Windows runners, configured in
  `.github/workflows/windows-build.yml`. Confirm a successful public run before
  submitting the application. The workflow creates unsigned review artifacts;
  signing integration remains pending provider approval and configuration.
- Current release is unsigned; we are requesting an eligibility review, not
  claiming that all technical enrollment requirements are already complete.

## Network/privacy disclosure for review

Captures and OCR inputs/results are processed locally. Automatic update checking
is enabled by default and fetches a small public version manifest from
raw.githubusercontent.com. GitHub can receive normal HTTP connection metadata.
The user can turn checking off in application settings; a manual check also
contacts GitHub. Clicking a download link opens the external browser. The landing
page is hosted by Vercel and downloads by GitHub. Their applicable privacy policies:

- https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement
- https://vercel.com/legal/privacy-policy

Do not claim the application never makes unsolicited network requests. Before
claiming compliance with SignPath's privacy requirements, add installer privacy
disclosure and an installation-time option to disable automatic update checks,
and review other dependencies' runtime network behavior.

## Prerequisites before requesting a production signature

1. Maintainer reviews terms, submits the application and receives approval.
2. Confirm project roles, MFA and repository integration permissions. Install the
   SignPath GitHub integration only after the maintainer authorizes its scope.
3. Add matching ProductName=Capcraft and product/file version metadata to our
   executable and installer, and enforce it in SignPath artifact configurations.
4. Build from an immutable reviewed revision on GitHub-hosted runners; pin CI
   actions/dependencies and validate OCR model hashes. Do not use a locally built
   upload as a substitute for SignPath's origin verification.
5. Upload the unsigned app artifact; request signing with manual approval; verify
   the returned app; package that app; request installer signing; verify again.
   Confirm supported Inno Setup and uninstaller signing handling with SignPath.
6. Use the actual approved organization/project/policy identifiers and a scoped
   GitHub Actions secret. Never put placeholder credentials into an active job.
7. Require valid Authenticode signatures, approved signer identity and timestamp
   on both artifacts. Test the final installer on another Windows PC.
8. Publish a new patch version (e.g. 1.2.1), new hashes and matching GPL source.
   Do not silently replace the already published unsigned v1.2.0 assets.

No workflow may automatically publish an unsigned fallback when signing fails.
Only after approval may the website/release policy add the required provider
credit: “Free code signing provided by SignPath.io, certificate by SignPath
Foundation”. Link this policy from the homepage and release/download pages then.

## Verification command

Run the following against final artifacts, using the **approved certificate's**
thumbprint (a public identifier, not a secret). Until signing, this must fail:

```powershell
./scripts/verify-signatures.ps1 `
  -AppPath 'dist-dev/Capcraft v1.2/Capcraft v1.2.exe' `
  -InstallerPath 'dist-dev/Installer/Capcraft_Setup_v1.2.0.exe' `
  -ExpectedThumbprint '<approved signing certificate thumbprint>'
```

This is a verification gate, not a signing implementation. A valid signature does
not guarantee SmartScreen warnings disappear immediately.

## Official references

- Application: https://signpath.org/apply.html
- Eligibility/policy: https://signpath.org/terms.html
- GitHub build provenance: https://docs.signpath.io/trusted-build-systems/github
- Windows verification: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-authenticodesignature
