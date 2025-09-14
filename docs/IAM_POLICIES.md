# IAM Least-Privilege Policy Samples

## S3 Write (artefacts/exports)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:PutObjectAcl"],
      "Resource": ["arn:aws:s3:::my-bucket/fmf/*"]
    }
  ]
}
```

## DynamoDB Write (upsert events)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:BatchWriteItem", "dynamodb:PutItem"],
      "Resource": ["arn:aws:dynamodb:us-east-1:123456789012:table/fmf-events"]
    }
  ]
}
```

## Redshift UNLOAD/COPY via S3 Staging

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift:GetClusterCredentials",
        "redshift-data:ExecuteStatement",
        "redshift-data:GetStatementResult"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": ["arn:aws:s3:::my-bucket/fmf/staging/*"]
    }
  ]
}
```

