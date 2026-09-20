# 0.3.7 publication handoff

The frozen qualification change was merged in PR #31 at
`cb29214e0ee83dfefa03639ba6ca368ec1a297e1`.
The generated 0.3.7 release PR #24 was merged at
`8cdf4ec9a27d93d46c7daeb921fc10cc2491eb30`.
Its final head was `f4d19a25e3c8fe64d49946b2d77a0c4d3b2bb020`.
CI run 35516025372 passed both Python jobs and distribution build;
conventional-title run 35516026407 passed.
The release PR changed only CHANGELOG.md and the release manifest.
Runtime source, tests and pyproject.toml match the qualified merge.

Dependency rqm-entanglement 0.2.2 is publicly available on PyPI.
Publication run 35512461375 in rqm-entanglement completed successfully.
The published dependency wheel's Python sources were verified byte-for-byte
against the dependency wheel in the certification archive.

The release merge message inherited a historical CI-skip directive from
the generated release body, preventing the push-triggered release workflow.
This documentation follow-up allows the existing release-management workflow
to process the merged release PR through the normal automation path.
No workflow, environment protection, runtime behavior or feature scope is changed.

GitHub release creation and protected PyPI publication must be verified
separately after release management runs. This record does not assert that
compiler publication has already completed.
