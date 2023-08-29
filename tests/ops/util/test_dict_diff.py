from fides.api.util.dict_diff import dict_diff


class TestDictDiff:
    def test_no_diff(self):
        dict1 = {"name": "John", "age": 25}
        dict2 = {"name": "John", "age": 25}
        before, after = dict_diff(dict1, dict2)
        assert before == {}
        assert after == {}

    def test_basic_diff(self):
        dict1 = {"name": "John", "age": 25}
        dict2 = {"name": "John", "age": 26}
        before, after = dict_diff(dict1, dict2)
        assert before == {"age": 25}
        assert after == {"age": 26}

    def test_diff_with_missing_key(self):
        dict1 = {"name": "John"}
        dict2 = {"name": "John", "age": 26}
        before, after = dict_diff(dict1, dict2)
        assert before == {}
        assert after == {"age": 26}

    def test_diff_with_none(self):
        dict1 = {"name": "John", "age": None}
        dict2 = {"name": "John", "age": 26}
        before, after = dict_diff(dict1, dict2)
        assert before == {"age": None}
        assert after == {"age": 26}

    def test_none_and_empty_string(self):
        dict1 = {"name": None}
        dict2 = {"name": ""}
        before, after = dict_diff(dict1, dict2)
        assert before == {}
        assert after == {}

    def test_nested_diff(self):
        dict1 = {"name": "John", "address": {"city": "New York", "zipcode": "10001"}}
        dict2 = {"name": "John", "address": {"city": "Brooklyn", "zipcode": "10001"}}
        before, after = dict_diff(dict1, dict2)
        assert before == {"address": {"city": "New York"}}
        assert after == {"address": {"city": "Brooklyn"}}

    def test_nested_diff_with_missing_key(self):
        dict1 = {"name": "John", "address": {"city": "New York"}}
        dict2 = {"name": "John", "address": {"city": "New York", "state": "NY"}}
        before, after = dict_diff(dict1, dict2)
        assert before == {}
        assert after == {"address": {"state": "NY"}}

    def test_multiple_nested_levels(self):
        dict1 = {"info": {"personal": {"name": "John"}}}
        dict2 = {"info": {"personal": {"name": "Doe"}}}
        before, after = dict_diff(dict1, dict2)
        assert before == {"info": {"personal": {"name": "John"}}}
        assert after == {"info": {"personal": {"name": "Doe"}}}

    def test_empty_dicts(self):
        dict1 = {}
        dict2 = {}
        before, after = dict_diff(dict1, dict2)
        assert before == {}
        assert after == {}

    def test_one_empty_dict(self):
        dict1 = {"name": "John"}
        dict2 = {}
        before, after = dict_diff(dict1, dict2)
        assert before == {"name": "John"}
        assert after == {}

    def test_nested_none_and_empty_string(self):
        dict1 = {"info": {"name": None}}
        dict2 = {"info": {"name": ""}}
        before, after = dict_diff(dict1, dict2)
        assert before == {}
        assert after == {}
