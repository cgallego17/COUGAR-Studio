import unittest
from display_ownership import DisplayOwnership


class OwnershipTests(unittest.TestCase):
    def test_cpu_never_pauses_vendor_and_preview_never_contacts_service(self):
        calls=[]
        control=DisplayOwnership(exchange=lambda mode: calls.append(mode))
        self.assertTrue(control.request(False))
        control.close()
        self.assertEqual(calls,[])
        control=DisplayOwnership(enabled=False,exchange=lambda mode: calls.append(mode))
        self.assertTrue(control.request(True))
        control.close()
        self.assertEqual(calls,[])

    def test_animation_waits_for_confirmation_then_cpu_releases_vendor(self):
        clock=[0]
        calls=[]
        def exchange(mode):
            calls.append(mode)
            return dict(ready=len(calls)>1,exclusive=mode)
        control=DisplayOwnership(exchange=exchange,clock=lambda:clock[0])
        self.assertFalse(control.request(True))
        clock[0]=1
        self.assertTrue(control.request(True))
        self.assertTrue(control.request(False))
        self.assertEqual(calls,[True,True,False])
        self.assertFalse(control.touched)

    def test_missing_renewals_expire_readiness_and_close_attempts_restoration(self):
        clock=[0]
        calls=[]
        def exchange(mode):
            calls.append(mode)
            if len(calls)>1:
                raise TimeoutError('Sin respuesta')
            return dict(ready=True,exclusive=mode)
        control=DisplayOwnership(exchange=exchange,clock=lambda:clock[0])
        self.assertTrue(control.request(True))
        clock[0]=1
        self.assertTrue(control.request(True))
        clock[0]=3.1
        self.assertFalse(control.request(True))
        control.close()
        self.assertEqual(calls[-1],False)

    def test_release_is_sent_even_if_acquisition_acknowledgement_was_lost(self):
        calls=[]
        def exchange(mode):
            calls.append(mode)
            if mode: raise TimeoutError()
            return dict(ready=True,exclusive=False)
        control=DisplayOwnership(exchange=exchange)
        self.assertFalse(control.request(True))
        self.assertTrue(control.request(False))
        self.assertEqual(calls,[True,False])


if __name__=='__main__': unittest.main()
