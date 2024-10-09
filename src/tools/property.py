import os


class Property(object):
    __props = {}

    filepath = os.path.join(os.path.dirname(__file__), os.path.pardir, ".config\\config")
    with open(filepath, "r") as f:
        for line in f:
            l = line.strip()
            if l and not l.startswith('#'):
                key_map = l.split('=')
                key_name = key_map[0].strip()
                key_value = '='.join(key_map[1:]).strip().strip()
                __props[key_name] = key_value
        print("properties init success")

    @staticmethod
    def get_property(property_name):
        try:
            return Property.__props.get(property_name)
        except KeyError:
            print("there is no that property name")
            return None


def main():
    print(Property.get_property("LONGPORT_APP_KEY"))


if __name__ == '__main__':
    main()
