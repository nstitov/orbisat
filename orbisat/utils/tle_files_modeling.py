def calc_tle_line_control_sum(line: str) -> int:
    control_sum = 0
    for letter in line[:-1]:
        if letter.isdigit():
            control_sum += int(letter)
        elif letter == "-":
            control_sum += 1
    return control_sum % 10


if __name__ == "__main__":
    import os

    tle_filename = "57173_2024-04-17.tle"
    tle_path = os.path.join(os.path.dirname(__file__), "..", "tle", tle_filename)

    with open(tle_path, "r", encoding="utf-8") as tle_file:
        line_1, line_2 = tle_file.read().strip().split("\n")
        control_sum_line_1 = calc_tle_line_control_sum(line_1)
        control_sum_line_2 = calc_tle_line_control_sum(line_2)

    print(control_sum_line_1, control_sum_line_2)
