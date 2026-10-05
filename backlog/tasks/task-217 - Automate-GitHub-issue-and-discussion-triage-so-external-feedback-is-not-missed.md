---
id: TASK-217
title: Automate GitHub issue and discussion triage so external feedback is not missed
status: To Do
assignee: []
created_date: '2026-10-05 21:27'
labels:
  - github
  - triage
  - community
dependencies: []
priority: medium
ordinal: 61000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Issue #155 (an external bug report) sat unanswered for 26 days. Two contributing factors were observed: the weekly ADR guardian bot opens issues with identical titles, burying human reports, and #155 was filed without a template, so it carried no label; label-based triage would have missed it too. Discussions were enabled on 2026-10-05 as a low-threshold feedback channel. Agreed design (layers A and B; C is out of scope): A) a scheduled GitHub Action, deterministic, no LLM, that finds open issues and discussions authored by anyone other than the maintainer or a bot without a maintainer response, labels new ones needs-triage, and after 3 days without response mentions the maintainer on the item (email notification). B) a lightweight session-start notice in this repo that prints one line ('N issues waiting for a reply, oldest D days') only when N > 0. Also: let the guardian bot update one rolling issue instead of opening new ones (verify current behaviour first), and set blank_issues_enabled: false in .github/ISSUE_TEMPLATE/config.yml with a contact link to Discussions.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A scheduled workflow lists open issues and discussions by non-maintainer, non-bot authors with no maintainer comment, using only GITHUB_TOKEN
- [ ] #2 New untriaged items get a needs-triage label; items unanswered for 3+ days get one maintainer mention, not repeated on every run
- [ ] #3 Bot-authored items (guardian audit) are excluded from the count
- [ ] #4 A session-start notice reports the waiting count and oldest age, silent when zero, fail-open when gh or the network is unavailable
- [ ] #5 Guardian bot behaviour checked: it reuses one rolling issue, or is changed to
- [ ] #6 Blank issues disabled with a contact link to Discussions
<!-- AC:END -->
