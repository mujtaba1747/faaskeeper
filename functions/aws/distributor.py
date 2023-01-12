import hashlib
import json
import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Set

import boto3

from faaskeeper.stats import StorageStatistics
from faaskeeper.watch import WatchEventType
from functions.aws.config import Config
from functions.aws.control.distributor_events import (
    DistributorCreateNode,
    DistributorDeleteNode,
    DistributorEvent,
    DistributorEventType,
    DistributorSetData,
)
from functions.aws.model.watches import Watches

mandatory_event_fields = [
    "op" "path",
    "session_id",
    "version",
    "sourceIP",
    "sourcePort",
    "data",
]

config = Config.instance(False)

"""
    The data received from the queue includes:
    - client IP and port
    - updates

    We support the following cases:
    - create_node - writing user node (no data) and writing children in parent node
    - set_data - update counter and data
    - delete_node - delete node and overwrite parent nodes
"""

# FIXME: configure
regions = ["us-east-1"]
# verbose_output = config.verbose
# verbose_output = False
# FIXME: proper data structure
region_clients = {}
region_watches = {}
epoch_counters: Dict[str, Set[str]] = {}
for r in regions:
    region_clients[r] = boto3.client("lambda", region_name=r)
    region_watches[r] = Watches(config.deployment_name, r)
    epoch_counters[r] = set()
executor = ThreadPoolExecutor(max_workers=2 * len(regions))

repetitions = 0
sum_total = 0.0
sum_notify = 0.0
sum_write = 0.0
sum_watch = 0.0
sum_watch_wait = 0.0


def get_object(obj: dict):
    return next(iter(obj.values()))


def launch_watcher(region: str, json_in: dict):
    """
    (1) Submit watcher
    (2) Wait for completion
    (3) Remove ephemeral counter.
    """
    # FIXME process result
    region_clients[region].invoke(
        FunctionName=f"{config.deployment_name}-watch",
        InvocationType="RequestResponse",
        Payload=json.dumps(json_in).encode(),
    )


# def query_watch_id(region: str, node_path: str):
#    return region_watches[region].get_watch_counters(node_path)


# def notify(write_event: dict, ret: dict):
#
#    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#        try:
#            s.settimeout(2)
#            logging.info("Notification", write_event)
#            source_ip = get_object(write_event["sourceIP"])
#            source_port = int(get_object(write_event["sourcePort"]))
#            s.connect((source_ip, source_port))
#            s.sendall(
#                json.dumps(
#                    {**ret, "event": get_object(write_event["user_timestamp"])}
#                ).encode()
#            )
#        except socket.timeout:
#            print(f"Notification of client {source_ip}:{source_port} failed!")


def handler(event: dict, context):

    events = event["Records"]
    logging.info(f"Begin processing {len(events)} events")

    processed_events = 0
    StorageStatistics.instance().reset()
    try:
        begin = time.time()
        watches_submitters = []
        for record in events:
            if "dynamodb" in record and record["eventName"] == "INSERT":
                write_event = record["dynamodb"]["NewImage"]
                event_type = DistributorEventType(int(write_event["type"]["N"]))
            elif "body" in record:
                write_event = json.loads(record["body"])
                event_type = DistributorEventType(int(write_event["type"]["N"]))
                if "data" in record["messageAttributes"]:
                    write_event["data"] = {
                        "B": record["messageAttributes"]["data"]["binaryValue"]
                    }
            else:
                raise NotImplementedError()

            logging.info("Begin processing event", write_event)

            # FIXME: hide under abstraction, boto3 deserialize
            operation: DistributorEvent
            counters = []
            watches = {}
            if event_type == DistributorEventType.CREATE_NODE:
                operation = DistributorCreateNode.deserialize(write_event)
            elif event_type == DistributorEventType.SET_DATA:
                operation = DistributorSetData.deserialize(write_event)
                hashed_path = hashlib.md5(operation.node.path.encode()).hexdigest()
                counters.append(
                    f"{hashed_path}_{WatchEventType.NODE_DATA_CHANGED.value}"
                    f"_{operation.node.modified.system.sum}"
                )
                watches = {
                    "path": operation.node.path,
                    "event": WatchEventType.NODE_DATA_CHANGED.value,
                    "timestamp": operation.node.modified.system.sum,
                }
            elif event_type == DistributorEventType.DELETE_NODE:
                operation = DistributorDeleteNode.deserialize(write_event)
            else:
                raise NotImplementedError()
            try:
                logging.info(f"Prepared event", write_event)
                begin_write = time.time()
                # write new data
                for r in regions:
                    ret = operation.execute(config.user_storage, epoch_counters[r])
                end_write = time.time()
                logging.info("Finished region operation")
                begin_watch = time.time()
                # start watch delivery
                for r in regions:
                    if event_type == DistributorEventType.SET_DATA:
                        watches_submitters.append(
                            executor.submit(launch_watcher, r, watches)
                        )
                end_watch = time.time()
                logging.info("Finished watch dispatch")
                for r in regions:
                    epoch_counters[r].update(counters)
                logging.info("Updated epoch counters")
                begin_notify = time.time()
                if ret:
                    # notify client about success
                    # notify(write_event, ret)
                    config.client_channel.notify(
                        operation.session_id,
                        get_object(write_event["user_timestamp"]),
                        write_event,
                        ret,
                    )
                    processed_events += 1
                else:
                    # notify(
                    #    write_event,
                    #    {"status": "failure", "reason": "distributor failured"},
                    # )
                    config.client_channel.notify(
                        operation.session_id,
                        get_object(write_event["user_timestamp"]),
                        write_event,
                        {"status": "failure", "reason": "distributor failured"},
                    )
                end_notify = time.time()
                logging.info("Finished notifying the client")
            except Exception:
                print("Failure!")
                import traceback

                traceback.print_exc()
                # notify(
                #    write_event, {"status": "failure", "reason": "distributor failure"},
                # )
                config.client_channel.notify(
                    operation.session_id,
                    get_object(write_event["user_timestamp"]),
                    write_event,
                    {"status": "failure", "reason": "distributor failured"},
                )
        logging.info("Start waiting for watchers")
        begin_watch_wait = time.time()
        for f in watches_submitters:
            f.result()
        end_watch_wait = time.time()
        end = time.time()
        logging.info("Finish waiting for watchers")

        global repetitions
        global sum_total
        global sum_notify
        global sum_write
        global sum_watch
        global sum_watch_wait
        repetitions += 1
        sum_total += end - begin
        sum_notify += end_notify - begin_notify
        sum_write += end_write - begin_write
        sum_watch += end_watch - begin_watch
        sum_watch_wait += end_watch_wait - begin_watch_wait
        if repetitions % 100 == 0:
            print("RESULT_TOTAL", sum_total)
            print("RESULT_NOTIFY", sum_notify)
            print("RESULT_WRITE", sum_write)
            print("RESULT_WATCH_WAIT", sum_watch)
            print("RESULT_WATCH_WAIT", sum_watch_wait)

    except Exception:
        print("Failure!")
        import traceback

        traceback.print_exc()

    # print(f"Successfully processed {processed_events} records out of {len(events)}")
    print(
        f"Request: {context.aws_request_id} "
        f"Read: {StorageStatistics.instance().read_units}\t"
        f"Write: {StorageStatistics.instance().write_units}"
    )
