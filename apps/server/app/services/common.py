from fastapi.encoders import jsonable_encoder


def serialize_model(item) -> dict:
    return jsonable_encoder({column.name: getattr(item, column.name) for column in item.__table__.columns})
