# Automated workflows

Add GitHub Actions workflow files here after the team's build and test commands are agreed.

No automated workflow is enabled by this scaffold.

| Candidate check | Decision needed |
| --- | --- |
| Code checks and unit tests | Languages, dependency versions and runnable commands |
| Integration tests using mocks | Shared interface and fixtures |
| Documentation checks | Agreed checks and exclusions |
| Board/simulation validation | Runner access, simulator and reproducible environment |
| Physical-arm tests | Lab access, supervision and a suitable execution procedure |

Keep secrets in the agreed GitHub secret storage. Physical-arm validation should have an explicit supervised procedure; do not treat a general hosted runner as a physical test environment.
