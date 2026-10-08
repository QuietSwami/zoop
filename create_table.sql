CREATE EXTERNAL TABLE cloudtrail_logs (
    eventversion STRING,
    useridentity STRUCT
        type: STRING, principalid: STRING, arn: STRING,
        accountid: STRING, invokedby: STRING, accesskeyid: STRING,
        username: STRING,
        sessioncontext: STRUCT
            attributes: STRUCT<mfaauthenticated: STRING, creationdate: STRING>,
            sessionissuer: STRUCT<type: STRING, principalid: STRING, arn: STRING, accountid: STRING, username: STRING>
        >
    >,
    eventtime STRING,
    eventsource STRING,
    eventname STRING,
    awsregion STRING,
    sourceipaddress STRING,
    useragent STRING,
    errorcode STRING,
    errormessage STRING,
    requestparameters STRING,
    responseelements STRING,
    requestid STRING,
    eventid STRING,
    eventtype STRING,
    recipientaccountid STRING
)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
LOCATION 's3://753b911cd7134b21a9b9113d4c878d9c-logs/AWSLogs/352909266144/CloudTrail/'
