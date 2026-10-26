"""Non-executing scope for the explicitly authorized public login demonstration."""
from dataclasses import dataclass
from enum import StrEnum


ORIGIN = 'https://the-internet.herokuapp.com'
LOGIN = ORIGIN + '/login'
AUTHENTICATE = ORIGIN + '/authenticate'
SECURE = ORIGIN + '/secure'
LOGOUT = ORIGIN + '/logout'


class DemoLoginScenario(StrEnum):
    ACCEPTED = 'accepted_login'
    REJECTED = 'rejected_login'
    LOGOUT = 'login_then_logout'


@dataclass(frozen=True)
class DemoLoginPlan:
    """Exact demo intent; it cannot authorize a browser, queue or arbitrary target."""
    scenario: DemoLoginScenario

    def __post_init__(self):
        if not isinstance(self.scenario, DemoLoginScenario):
            raise ValueError('An explicit typed demo scenario is required.')

    @property
    def execution_authorized(self):
        return False

    @property
    def max_submissions(self):
        return 1

    @property
    def expected_document(self):
        return LOGIN if self.scenario == DemoLoginScenario.REJECTED else SECURE

    @property
    def expected_message(self):
        return ('Your password is invalid!' if self.scenario == DemoLoginScenario.REJECTED
                else 'You logged into a secure area!')

    def redirect_destination(self, source, status, location):
        """Validate exact known transitions; never grant generic redirect authority."""
        if type(status) is not int or status != 302:
            raise ValueError('The expected demo redirect was not observed.')
        if source == AUTHENTICATE:
            expected = self.expected_document
        elif source == LOGOUT and self.scenario == DemoLoginScenario.LOGOUT:
            expected = LOGIN
        else:
            raise ValueError('Unexpected demo redirect source.')
        if location not in (expected, expected[len(ORIGIN):]):
            raise ValueError('Unexpected demo redirect destination.')
        return expected
