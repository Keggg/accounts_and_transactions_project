from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from uuid import UUID

from account.account import Account


class ObjectNotFound(ValueError):
    ...


@dataclass
class AccountDatabase(ABC):  # <---- INTERFACE
    def save(self, account: Account) -> None:
        print("I am going to save this account:", account)
        return self._save(account=account)

    @abstractmethod
    def _save(self, account: Account) -> None:
        ...

    @abstractmethod
    def clear_all(self) -> None:
        ...

    @abstractmethod
    def get_objects(self) -> List[Account]:
        ...

    @abstractmethod
    def get_object(self, id_: UUID) -> Account:
        ...
    
    @abstractmethod
    def delete(self, account: Account) -> None:
        ...

@dataclass
class TransactionDatabase(ABC):  # <---- INTERFACE
    def save(self, source_account: Account, target_account: Account, balance_brutto, db) -> None:
        print("I am going to save this transaction: FROM", source_account, "TO", target_account)
        return self._save(source_account=source_account, target_account=target_account, balance_brutto=balance_brutto, db=db)

    @abstractmethod
    def _save(self, source_account: Account, target_account: Account, balance_brutto, db) -> None:
        ...

    @abstractmethod
    def clear_all(self) -> None:
        ...

    @abstractmethod
    def get_objects(self) -> List[Account]:
        ...

    @abstractmethod
    def get_object(self, id_: UUID) -> Account:
        ...

    @abstractmethod
    def delete(self, account: Account) -> None:
        ...
