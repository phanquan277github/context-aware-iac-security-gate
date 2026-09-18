# Pilot Metadata Domains

## Business Metadata

### environment
- dev
- staging
- prod

### asset_criticality
- low
- medium
- high
- critical

### data_sensitivity
- public
- internal
- sensitive

## Infrastructure-Derived Features

### internet_exposure
- none
- limited
- high

### privilege_impact
- low
- medium
- high

### reachability
- internal
- internet

## Ordinal Encoding

environment:
dev=1
staging=2
prod=3

asset_criticality:
low=1
medium=2
high=3
critical=4

data_sensitivity:
public=1
internal=2
sensitive=3

internet_exposure:
none=0
limited=1
high=2

privilege_impact:
low=1
medium=2
high=3

reachability:
internal=0
internet=1
