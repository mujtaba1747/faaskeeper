from enum import Enum
from os import environ
from typing import Optional

import functions.aws.control as control
import functions.aws.model as model


class Storage(Enum):
    PERSISTENT = 0
    KEY_VALUE = 1


class QueueType(Enum):
    DYNAMODB = 0
    SQS = 1


class Config:

    _instance: Optional["Config"] = None

    def __init__(self, with_distributor_queue: bool = True):
        self._verbose = bool(environ["VERBOSE"])
        self._deployment_name = environ["DEPLOYMENT_NAME"]

        # configure user storage handle
        self._user_storage_type = {
            "persistent": Storage.PERSISTENT,
            "key-value": Storage.KEY_VALUE,
        }.get(environ["USER_STORAGE"])
        self._user_storage: model.UserStorage
        if self._user_storage_type == Storage.PERSISTENT:
            self._user_storage = model.UserS3Storage(
                bucket_name=f"faaskeeper-{self._deployment_name}-data"
            )
        else:
            self._user_storage = model.UserDynamoStorage(
                table_name=f"faaskeeper-{self._deployment_name}-data"
            )

        # configure system storage handle
        self._system_storage_type = {"key-value": Storage.KEY_VALUE}.get(
            environ["SYSTEM_STORAGE"]
        )
        if self._system_storage_type == Storage.KEY_VALUE:
            self._system_storage = model.SystemDynamoStorage(
                f"faaskeeper-{self._deployment_name}"
            )
        else:
            raise RuntimeError("Not implemented!")

        # configure distributor queue
        self._distributor_queue: Optional[control.DistributorQueue]
        if with_distributor_queue:
            self._distributor_queue_type = {"dynamodb": QueueType.DYNAMODB}.get(
                environ["DISTRIBUTOR_QUEUE"]
            )
            if self._distributor_queue_type == QueueType.DYNAMODB:
                self._distributor_queue = control.DistributorQueueDynamo(
                    f"faaskeeper-{self._deployment_name}"
                )
            else:
                raise RuntimeError("Not implemented!")
        else:
            self._distributor_queue = None

    @staticmethod
    def instance(with_distributor_queue: bool = True) -> "Config":
        if not Config._instance:
            Config._instance = Config(with_distributor_queue)
        return Config._instance

    @property
    def verbose(self) -> bool:
        return self._verbose

    @property
    def deployment_name(self) -> str:
        return self._deployment_name

    @property
    def user_storage(self) -> model.UserStorage:
        return self._user_storage

    @property
    def system_storage(self) -> model.SystemStorage:
        return self._system_storage

    @property
    def distributor_queue(self) -> Optional[control.DistributorQueue]:
        return self._distributor_queue
