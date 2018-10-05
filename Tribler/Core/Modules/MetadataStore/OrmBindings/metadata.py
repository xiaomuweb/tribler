from datetime import datetime

from pony import orm

from Tribler.Core.Modules.MetadataStore.serialization import MetadataTypes, MetadataPayload, DeletedMetadataPayload
from Tribler.pyipv8.ipv8.keyvault.crypto import ECCrypto

EMPTY_SIG = '0' * 64


def define_binding(db):
    class Metadata(db.Entity):
        rowid = orm.PrimaryKey(int, auto=True)
        metadata_type = orm.Discriminator(int)
        _discriminator_ = MetadataTypes.TYPELESS.value
        signature = orm.Optional(buffer, default=EMPTY_SIG)
        timestamp = orm.Optional(datetime, default=datetime.utcnow)
        tc_pointer = orm.Optional(int, size=64, default=0)
        public_key = orm.Optional(buffer, default='\x00' * 74)
        addition_timestamp = orm.Optional(datetime, default=datetime.utcnow)
        deleted = orm.Optional(bool, default=False)
        _payload_class = MetadataPayload

        def serialized(self, key=None):
            return self._payload_class(**self.to_dict()).serialized(key)

        def serialized_delete(self, key):
            """
            Create a special command to delete this metadata and encode it for transfer.
            """
            my_dict = Metadata.to_dict(self)
            my_dict.update({"metadata_type": MetadataTypes.DELETED.value,
                            "delete_signature": self.signature})
            print my_dict
            return DeletedMetadataPayload(**my_dict).serialized(key)

        def to_file(self, filename, key=None):
            with open(filename, 'wb') as output_file:
                output_file.write(''.join(self.serialized(key)))

        def to_delete_file(self, key, filename):
            with open(filename, 'wb') as output_file:
                output_file.write(''.join(self.serialized_delete(key)))

        def sign(self, key):
            self.public_key = buffer(key.pub().key_to_bin())
            _, self.signature = self.serialized(key)

        def has_valid_signature(self):
            crypto = ECCrypto()
            return crypto.is_valid_public_bin(str(self.public_key)) \
                     and self._payload_class(**self.to_dict()).has_valid_signature()

        @classmethod
        def from_payload(cls, payload):
            return cls(**payload.to_dict())

        @classmethod
        def from_dict(cls, dct):
            return cls(**dct)

    return Metadata
