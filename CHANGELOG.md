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



