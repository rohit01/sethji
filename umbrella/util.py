def convert_none_into_blank_values(details):
    for k, v in details.items():
        if v == None:
            details[k] = ''
    return details
