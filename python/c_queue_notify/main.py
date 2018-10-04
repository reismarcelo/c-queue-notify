# -*- mode: python; python-indent: 4 -*-
import _ncs
import ncs
from ncs.dp import Action
from ncs.maapi import Maapi
import requests
import jinja2


# ---------------------------------------------
# ACTIONS
# ---------------------------------------------
class NotifyAction(Action):
    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):

        def iterate(keypath, op, old_value, new_value):
            if op == ncs.MOP_DELETED and len(keypath) > 2 and kp_value(keypath[0]) == 'commit-queue':
                # /ncs:services/cq-notify-test:c-queue-test1/vrf{cust4}/plan/commit-queue
                self.log.info("Commit-queue completed for notifier {}, service instance {}.".format(
                    input.kicker_id,
                    kp_value(keypath[2])
                ))
                send_rest_notification(service=kp_value(keypath[2]), notifier=input.kicker_id)
                return ncs.ITER_STOP
            else:
                return ncs.ITER_RECURSE

        def send_rest_notification(**kwargs):
            # Retrieve configured REST parameters
            with ncs.maapi.single_read_trans(uinfo.username, "system") as read_t:
                rest_params = ncs.maagic.get_node(read_t, kp).rest
                uri = rest_params.uri
                source_data = rest_params.payload
                rest_user = rest_params.username
                read_t.maapi.install_crypto_keys()
                rest_pass = _ncs.decrypt(rest_params.password)

            # Process source_data through jinja2
            jinja_env = jinja2.Environment(autoescape=True, trim_blocks=True, lstrip_blocks=True)
            data = jinja_env.from_string(source_data).render(kwargs)

            # Send REST notification
            try:
                response = requests.post(url=uri, auth=(rest_user, rest_pass), data=data)
                response.raise_for_status()
                self.log.info("REST notification sent successfully: status code {}.".format(response.status_code))
            except requests.exceptions.RequestException as e:
                self.log.error("REST notification failed: {}".format(e))

        with Maapi() as m:
            try:
                t = m.attach(input.tid)
                t.diff_iterate(iterate, ncs.ITER_WANT_P_CONTAINER)
            finally:
                m.detach(input.tid)


def kp_value(kp_element):
    """
    Get the value of a keypath element as native Python type
    :param kp_element: an element of a keypath (HKeypathRef)
    :return: The element .as_pyval() or a list of it. If element is an XmlTag return its string value
    """
    if isinstance(kp_element, tuple):
        values = [value.as_pyval() for value in kp_element]
        if len(values) == 1:
            values = values[0]

        return values

    # This an xmltag element, i.e. not a type-value key-path element
    return str(kp_element)


# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class Main(ncs.application.Application):
    def setup(self):
        self.log.info('Main RUNNING')

        # Registration of action callbacks
        self.register_action('c-queue-notify-action', NotifyAction)

    def teardown(self):
        self.log.info('Main FINISHED')
