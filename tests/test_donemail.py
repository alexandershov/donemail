import donemail

# TODO: monkeypatch send_email

BOB = 'bob@example.com'


def test_context_manager():
    with donemail.donemail(BOB):
        pass


def test_decorator():
    @donemail.donemail(BOB)
    def add(x, y):
        return x + y

    add(1, 2)