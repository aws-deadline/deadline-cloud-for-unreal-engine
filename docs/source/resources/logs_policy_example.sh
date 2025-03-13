aws logs put-account-policy
--policy-name "MaskOpenJDEnvSecrets"
--policy-type DATA_PROTECTION_POLICY
--scope ALL
--policy-document '{
  "Name": "openjd_data_protection",
  "Description": "Hides openjd_env log line data which may be setting sensitive info",
  "Version": "2021-06-01",
  "Configuration": {
    "CustomDataIdentifier": [
      {"Name": "OpenjdEnv", "Regex": "openjd_env:\s*[^=]+=.*"}
    ]
  },
  "Statement": [
    {
      "Sid": "audit-policy",
      "DataIdentifier": [
        "OpenjdEnv"
      ],
      "Operation": {
        "Audit": {
          "NoFindingsDestination": {}
        }
      }
    },
    {
      "Sid": "redact-policy",
      "DataIdentifier": [
        "OpenjdEnv"
      ],
      "Operation": {
        "Deidentify": {
          "MaskConfig": {}
        }
      }
    }
  ]
}'