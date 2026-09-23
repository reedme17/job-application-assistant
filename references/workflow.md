# Browser and application workflow

## Source access

Use the browser tool's documented controls and observed page state. Do not infer hidden APIs, extract cookies, or reuse session credentials through unrelated networking tools. User login alone is not platform authorization for automated access. Low speed, manual triggering, and stopping before Submit do not remove platform restrictions.

LinkedIn and Indeed restrict third-party automation, including extraction or filling, not just submission. Do not assume a supplied search URL makes automated access permitted. Use an explicitly permitted integration/access route where established; otherwise ask the user to provide job URLs or listing/JD text through permitted means and continue on employer sites whose access rules allow the requested operation. If current permission is unclear, verify official source rules. Do not bypass restrictions, CAPTCHAs, rate limits, or blocks.

Policy references (verify when needed; not permission grants):
- https://www.linkedin.com/help/linkedin/answer/a1340567/automated-activity-on-linkedin
- https://www.indeed.com/legal

## Extract and deduplicate

Respect the specified page range or job count. If unspecified, process the current results page, including its ordinary scroll-loaded cards; do not automatically expand across every pagination page. Save progress incrementally.

For each listing, inspect visible card data and open its details only when needed. Record the actual link and its role: source search page, JD, or employer application. An onsite modal may have no separate application URL; keep it null and retain the JD URL. Follow ordinary observed Apply links, preserving required parameters. Check that the destination corresponds to the same employer and role before any personal-data entry.

Prefer deduplication by ATS/provider + observed job ID, then exact canonical job URL. Remove only clearly recognized tracking parameters for comparison, retaining original navigation URLs. Do not strip all query parameters: some identify the vacancy. Company/title/location similarity is a potential duplicate to review, not proof. Do not collapse distinct requisitions merely because titles match.

For infinite scrolling, track unique observed job identifiers; stop when the requested limit is met or no new cards appear after a reasonable bounded check. Record coverage and blockers honestly. A job can expire between discovery and filling; verify it is still open.

## Prepare and fill

Treat Greenhouse, Lever, Ashby, Workday, and custom portals as possible destinations, not guaranteed supported adapters. Inspect each live form and available controls; never assume fixed selectors or universal field order.

1. Verify employer, role, application URL and the correct job-specific resume.
2. Fill personal/contact, education, employment and portfolio fields from the approved profile or verified resume. Match labels and meanings rather than field positions. Inspect parsed resume fields for mistakes.
3. Answer screening questions using evidence. Work authorization and future sponsorship are separate questions. Years of experience must follow confirmed dates and the actual skill asked about; do not sum overlapping jobs or round up to satisfy a requirement.
4. Use explicitly approved salary, location, relocation and availability answers, with the right currency/time unit and region. If context differs from the saved answer's scope, leave unresolved.
5. For demographic, disability, veteran or other voluntary sensitive fields, use only the user's explicit selection. Do not infer answers or select “prefer not to say” as an automatic default. For unknown required fields, stop that application and explain what is missing; other independent preparation can continue.
6. Do not accept privacy consents, legal certifications, electronic signatures, background-check authorizations or optional marketing choices unless the user has explicitly authorized the specific choice and scope. Leave final attestations for manual review. Do not create accounts or change credentials under a generic fill-form request.
7. Navigation buttons may submit a step or application. Use Next/Continue only after inspecting their meaning; if ambiguous, stop. Do not press Enter in a way that might submit. Assessments and interview exercises go to the user.
8. Verify populated controls against intended values, including dropdowns, dates, required fields, uploaded filename, and parser-generated fields. Record unresolved issues. Never report completion solely because typing succeeded.

If login, MFA, CAPTCHA, or a site block appears, save state and ask the user to handle it normally. Do not blindly retry. After a failure that might have submitted, check available confirmation evidence before another attempt to avoid duplicate applications.

## Final review and resume

Show a short review: role/company; exact resume file; key changes; screening answers needing attention; and unresolved fields. Set `review_ready` only when required information is complete and the page is ready for manual final review/submission. Otherwise use `needs_info` or `blocked`.

Do not accumulate many fragile prefilled tabs. Finish the current application handoff before moving on, unless the user specifically wants multiple tabs. On another computer, reload local records and re-check page state; saved files do not preserve live browser forms or sessions.
