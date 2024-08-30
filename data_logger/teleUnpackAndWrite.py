import json

from influxdb_client import Point


def json_to_point(json_string):
    data = json.loads(json_string)
    point = Point(data["measurement"])  # telemetry
    print(f'meas: {data["measurement"]}')
    if "tags" in data:
        print(" tags: ", end="")
        for tag_key, tag_value in data["tags"].items():
            point.tag(tag_key, tag_value)
            print(f"{tag_key}: {tag_value}; ", end="")
        print("")
    if "fields" in data:
        for field_key, field_value in data["fields"].items():
            points = dig_points(field_key, field_value)
            for item in points:
                point.field(item[0], item[1])

    if "time" in data:
        point.time(data["time"])
        print(f' time: {data["time"]}')
    return point


def dig_points(name, field_value):
    points = []
    if type(field_value) == list:
        for i, el in enumerate(field_value):
            points += dig_points(name + f"_{i}", el)
    elif type(field_value) == dict:
        for el_key, el_val in field_value.items():
            points += dig_points(name + f"_{el_key}", el_val)
    else:
        points += [(name, field_value)]
    return points


# пример
# json_string = '{"measurement": "temperature", "tags": {"location": "room1", "sensor": "A"}, "fields": {"value": 23.4, "unit": "C"}}'
# point = json_to_point(json_string)
# print(point.to_line_protocol())


def create_msg(pack_ind, src_ind, fields_name_list, fields_val_list):
    msg = f"{packets[pack_ind]},источник={src[src_ind]} "
    for i, el in enumerate(fields_name_list):
        msg += f"{el}={fields_val_list[i]} "
    return msg


# _write_client.write("my-bucket", "my-org", {"measurement": "h2o_feet", "fields": {"water_level": 1.0}})
# writer.write(bucket="testing", record="sensor temp=23.3")
# writer.write(bucket="test", record="БЦВМ,источник=магнитометр температура=23.3")

src = []

packets = [
    "БЦВМ",
    "Выносной магнитометр",
    "Датчики освещённости",
    "Датчик Солнца",
    "Краткий статус БС",
    "Статус СЭП1",
    "Статус СЭП2",
    "Статус ПрмПрд",
    "Статус СУД боковые панели",
    "Статус СУД торцевые платы",
    "Навигатор",
    "Навигатор расширенный",
    "ДПП",
    "Ориентация КВ и ФК",
]

fields_1 = []
fields_2 = []
fields_3 = []
fields_4 = []
fields_5 = []
fields_6 = []
fields_7 = []
fields_8 = []
fields_9 = []
fields_10 = []
fields_11 = []
fields_12 = []
fields_13 = []
fields_14 = []
