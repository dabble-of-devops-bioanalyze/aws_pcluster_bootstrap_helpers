from datetime import datetime
from typing import List

from mypy_boto3_logs.client import CloudWatchLogsClient
from mypy_boto3_logs.type_defs import GetLogEventsResponseTypeDef
from mypy_boto3_logs.type_defs import OutputLogEventTypeDef


def get_human_readable_time(last_time_stamp):
    return datetime.fromtimestamp(last_time_stamp / 1000.0).isoformat()


def get_log_events_wrapper(
    client: CloudWatchLogsClient,
    log_group,
    log_stream_name,
    start_time=0,
    skip=0,
    start_from_head=True,
) -> List[OutputLogEventTypeDef]:
    """
    A generator for log items in a single stream. This will yield all the
    items that are available at the current moment.

    Completely stole this from here
    https://airflow.apache.org/docs/apache-airflow/1.10.5/_modules/airflow/contrib/hooks/aws_logs_hook.html

    :param client: boto3.client('cloudwatch')
    :param log_group: The name of the log group.
    :type log_group: str
    :param log_stream_name: The name of the specific stream.
    :type log_stream_name: str
    :param start_time: The time stamp value to start reading the logs from (default: 0).
    :type start_time: int
    :param skip: The number of log entries to skip at the start (default: 0).
        This is for when there are multiple entries at the same timestamp.
    :type skip: int
    :param start_from_head: whether to start from the beginning (True) of the log or
        at the end of the log (False).
    :type start_from_head: bool
    :rtype: dict
    :return: | A CloudWatch log event with the following key-value pairs:
             |   'timestamp' (int): The time in milliseconds of the event.
             |   'message' (str): The log event data.
             |   'ingestionTime' (int): The time in milliseconds the event was ingested.
    """

    next_token = None

    event_count = 1
    while event_count > 0:
        if next_token is not None:
            token_arg = {"nextToken": next_token}
        else:
            token_arg = {}

        response: GetLogEventsResponseTypeDef = client.get_log_events(
            logGroupName=log_group,
            logStreamName=log_stream_name,
            startTime=start_time,
            startFromHead=start_from_head,
            **token_arg,
        )

        events = response["events"]
        event_count = len(events)

        if event_count > skip:
            events = events[skip:]
            skip = 0
        else:
            skip = skip - event_count
            events = []

        for ev in events:
            yield ev

        if "nextForwardToken" in response:
            next_token = response["nextForwardToken"]
        else:
            return


def print_logs(
    client: CloudWatchLogsClient,
    log_stream_name: str,
    log_group: str = "/aws/batch/job",
    start_time: int = 0,
) -> int:
    log_events = get_log_events_wrapper(
        client,
        log_group=log_group,
        log_stream_name=log_stream_name,
        start_time=start_time,
    )

    last_time_stamp = start_time
    for log_event in log_events:
        last_time_stamp = log_event["timestamp"]
        human_timestamp = get_human_readable_time(last_time_stamp)
        message = log_event["message"]
        print(f"[{human_timestamp}] {message}")

    if last_time_stamp > 0:
        last_time_stamp = last_time_stamp + 1

    return last_time_stamp
