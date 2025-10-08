## 0.6.4 (2025-10-08)




## 0.6.3 (2025-09-30)



### Bug Fixes
* skip a test that passes in GitHub but fail in CodeBuild (#213) ([`7721f28`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/7721f289c2f28e0626927ab9033de2ffb632c0a0))

## 0.6.2 (2025-09-30)


### Features
* Update Perforce utils to sync dependent files (#207) ([`4a60a67`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/4a60a67566723bef9d8aa982947ac12d7237312b))
* Update Perforce utils to sync dependent files ([`4a60a67`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/4a60a67566723bef9d8aa982947ac12d7237312b))
* UI Simplification ([`ca11214`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/ca1121433f8da36d1b32bfec3db937c636dddc19))
* UI Simplification ([`ca11214`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/ca1121433f8da36d1b32bfec3db937c636dddc19))
* Visibility handling updates ([`ca11214`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/ca1121433f8da36d1b32bfec3db937c636dddc19))

### Bug Fixes
* Logging configuration issue (#210) ([`53ba947`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/53ba9477472fb65ec88e9fc207a19ad6d7ea7b6b))
* fixed log config. Added troubleshooting guide for misconfigured MRQ. Also added more logs ([`53ba947`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/53ba9477472fb65ec88e9fc207a19ad6d7ea7b6b))
* Caching and using our deadline client for precache_clients method due to potential race condition with underlying clients cached with lru_cache (#205) ([`1f177db`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/1f177db20b08f143e7dd10df98bbdc9d9fa47ea2))
* Fix the problem where p4 utils is unable to log stuff ([`4a60a67`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/4a60a67566723bef9d8aa982947ac12d7237312b))
* chunk_size parameter in runData section (#204) ([`4d79a2d`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/4d79a2d9dc4a9995c3f5695ff9cf7b069b9826c1))
* resolve formatting issues ([`bb89146`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/bb89146549edc5ae420b84bddceed2778b109d9c))
* sonarqube issues fix ([`ca11214`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/ca1121433f8da36d1b32bfec3db937c636dddc19))
* Add job ref to step in UnrealOpenJob.from_data_asset ([`ca11214`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/ca1121433f8da36d1b32bfec3db937c636dddc19))
* remove code duplication ([`ca11214`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/ca1121433f8da36d1b32bfec3db937c636dddc19))
* remove unused code ([`ca11214`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/ca1121433f8da36d1b32bfec3db937c636dddc19))
* Autodetect Project Plugins (#180) ([`86cb4a6`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/86cb4a60059058217b6750cf722756857fc4889c))
* Autodetect Project Plugins ([`86cb4a6`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/86cb4a60059058217b6750cf722756857fc4889c))

## 0.6.1 (2025-08-01)


### Features
* Using precache_clients in background thread for faster initial job submission (#178) ([`49870d2`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/49870d2af6dbbeac8f5cb9627db042cccdf93373))
* MRQ Job validation error message fixes (#161) ([`b26a928`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/b26a928dd8b1f6cbdc75187b4eb9b6541ba91c92))

### Bug Fixes
* Switching to use openjd_redacted_env for potentially sensitive environment variables. (#181) ([`586ca74`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/586ca74c5c9e5d4048edd29801336a4f9728bd14))
* Support ExtraCmdArgs several inputs (#177) ([`26548a5`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/26548a5ecc0f45913c3cf0ea4785f3602abd53b4))
* Error message in field: Contains empty elements or more than 50 of them with UE 5.5.4 (#154) (#176) ([`d2eee55`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/d2eee55fea9394c1a0857d52653d71868fddb8be))
* Parameters definitions are empty in MRQ UI when you first time create the job. But if you reset the data asset, then they appear (#175) ([`afd180c`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/afd180cb90c97fe52f56667cd8b1f2d031b44cc7))
* Resolve deprecation warnings (#174) ([`9a514bf`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/9a514bf4d5a24e0656c539ff0446851b86dd26b9))

## 0.6.0 (2025-07-16)


### Features
* Update render_job template to include Conda variables for SMF and update related docs (#164) ([`8c73fb1`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/8c73fb144aff7ed40ae64ca54773f999b8ed7670))
* persistent UI settings (#160) ([`f6a6530`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/f6a65301953e432824b02fd361fac4e583f7844e))
* Input validation (#145) ([`54747db`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/54747db678b9e27a117f9e6e8df20b78c8995edf))
* Developer Settings refactor (#142) ([`66996e6`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/66996e6f990ef8959956163fa0570d2df7d412a3))
* Developer Settings fix. Linters compliance ([`66996e6`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/66996e6f990ef8959956163fa0570d2df7d412a3))
* P4 Sync improvements (#144) ([`2e9800b`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/2e9800baf9702ddc081df7b474de546189ccb64d))
* P4 sync improvements ([`2e9800b`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/2e9800baf9702ddc081df7b474de546189ccb64d))
* P4 sync improvements. List only unique dependencies ([`2e9800b`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/2e9800baf9702ddc081df7b474de546189ccb64d))
* Support MPQ asset as render argument (#143) ([`f66391a`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/f66391a9a72488f5d9f8ac15e44b8533caf3546e))

### Bug Fixes
* Pinning model dependency to 0.8.x to prevent minor model updates from breaking us unexpectedly (#162) ([`7a2f824`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/7a2f824d5c10ce3405440944d9ca8c3ec960b887))
* Using parse_model to instantiate classes using default context ([`66497e1`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/66497e128fd1df79cf3ef0fd00ce835908aa052e))

## 0.5.0 (2025-03-17)


### Features
* support AWS Secrets Manager (#130) ([`b37d188`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/b37d18817ebe050cdf259d29be52f06dcfe65fef))
* Adding checks with warnings to the build_plugin script for common configuration problems which can cause job failures. (#133) ([`f546e53`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/f546e53bb66a28c0049cfc902d5aa84c0ee342a9))
* Switching to sorting tasks by ChunkId in DCM (#132) ([`1722d6e`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/1722d6ef8828b6db49cc63cd42429cb6ad885f3b))
* support Perforce (#101) ([`fa2ef80`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/fa2ef80309807dbb0c901e2d4c896f1681a8b898))


## 0.4.0 (2025-03-01)


### Features
* Updating build_plugin.py support script to add option for installing test content, skipping binary installation, and allowing running from the scripts directory. (#120) ([`61bb7d6`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/61bb7d653afda86c638286939bdf6e1b42c6b0fb))
* Custom Submitters (#89) ([`b79202c`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/b79202ce1d2ea31b03df11f9e280dfa1099677a0))
* Updating build_plugin.py support script to remove unnecessary archiving and upload support and add additional installation support for building python libraries and installing both binaries and python code to the given Unreal installation plugins folder with a new --install option (#102) ([`2a63379`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/2a633797280b72879d88d4179572b0fe39e36535))
* Adding PythonRequirements to plugin to optionally install Python dependencies automatically. (#98) ([`26259ee`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/26259ee85fc1e754e38738567456d65934164246))


## 0.3.0 (2024-12-10)


### Features
* ExtraCmdArgsFile parameter to handle param length limit (#96) ([`3cc407d`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/3cc407de34d5204f8fcf3146e0394c39dbf44aa8))
* split MRQ Job level sequence into shot chunks (#78) ([`d47e734`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/d47e734fe0dec6b34d60065d2a778bd253a9c465))
* Script for producing plugin prebuild archive (#77) ([`57313a8`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/57313a8e2f450a7d34f3211a0b0fdd02d506506c))
* Updating default installed version path of unreal to 5.4 (Latest official release).  Changing some comments to reflect support for 5.2 and above.  Adding a registry check for most recently installed version which will override default when found.  It's no longer necessary for 'UnrealDeadlineCloudService' Plugins folder to exist for installation to work, only the Plugins folder needs to exist. (#72) ([`d8e2e6a`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/d8e2e6a92da2125a24617933eb8bd99886331abc))

### Bug Fixes
* Updating CHANGELOG processing to handle recent breaking changes in python-semantic-release (#95) ([`0081d9d`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/0081d9dae949643972ba5bd465f08ba1fb943344))
* Importing logger after adding install libraries to sys.path.  Setting uninstall files in submitter installer.  Adding logger to submitter installer. (#93) ([`417c605`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/417c605b14625ad59d143dcfdcc6dd67ba68c52f))

## 0.2.2 (2024-06-19)



### Bug Fixes
* rename duplicate prefix argument to unreal-plugin-directory (#62) ([`22bf103`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/22bf103a60b4647a3e4af0c951d68380c9100ca4))

## 0.2.1 (2024-05-01)

### Dependencies
* update deadline requirement from ==0.47.* to ==0.48.* (#52) ([`bf6ae92`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/bf6ae92a303a2f5b57fafef7a8a34939257a99bf))


## 0.2.0 (2024-04-01)

### BREAKING CHANGES
* public release (#38) ([`815940b`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/815940b5eb10681896d5e9422129cd2d62ec31ba))
* update minimum python version to 3.9 in hatch.toml (#38) ([`815940b`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/815940b5eb10681896d5e9422129cd2d62ec31ba))


### Bug Fixes
* Naming cleanup. (#42) ([`704b3d4`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/704b3d4988096a45341dfe17a845b5ef66b5fd53))


## 0.1.2 (2024-03-26)


### Features
* Adds telemetry events to submitter and adaptor (#27) ([`62c5e9e`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/62c5e9e1aa39775d6e531755b3e99ef13c28714f))


## 0.1.1 (2024-03-15)

### Chores
* update deps deadline-cloud 0.40 (#25) ([`cebd1c4`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/8817e0ffd4c65ced11f4c09645367894793ef43f))

## 0.1.0 (2024-03-08)

### BREAKING CHANGES
* **deps**: update openjd-adaptor-runtime to 0.5 (#21) ([`1c52c77`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/1c52c778b46558a6e212775f8884471a83bf63de))
* renamed openjd-unreal-engine to unreal-engine-openjd (#11) ([`2a6bd76`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/2a6bd76d269ce3cfe30028d73f29d4ecc616024b))


### Bug Fixes
* Add imports to init_unreal to fully load the plugin. (#18) ([`affa98f`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/affa98f12989bed4a92eba58e1e4db5d405a7dc2))

## 0.0.3 (2024-02-22)



### Bug Fixes
* add executable bit to depsBundle (#9) ([`c07eff7`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/c07eff7ade5f8e73cfdc2a43d85e7bf9f0df5258))

## 0.0.2 (2024-02-21)



### Bug Fixes
* **ci**: update project name and add another entrypoint for the adaptor ([`67818a6`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/67818a6a93344ac9d82389a6f9dfe1d36eb86a6e))

## 0.0.1 (2024-02-21)


### Features
* initial integration (#1) ([`96ff05e`](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/commit/96ff05e787fabfc375c7e379e9b87cd574774869))



