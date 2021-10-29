from fetch_approved_routes_dataset import fetch_dataset_insistently, defaults as fetch_defaults
from compare_and_update_routes_dataset import compare_and_update_dataset, defaults as compare_defaults


if __name__ == '__main__':
    path_and_name = fetch_dataset_insistently(**fetch_defaults)
    compare_and_update_dataset(**compare_defaults, **path_and_name)
