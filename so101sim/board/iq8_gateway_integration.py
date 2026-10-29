"""VENTUNO Q IQ8 gateway scaffold: real MCU approval is REQUIRED for motion.

A TCP link can be tested with connectivity_probe.py, but this integration file
intentionally refuses to produce MCU-approved actions until the actual
Arduino App Lab Bridge/RPC and STM32H5F5 firmware have been connected.
"""
import json
import socket
import time

class MCUApprovalRequired(RuntimeError):
    pass


def read_mcu_approved_action():
    """Implement after validating real STM32H5F5 firmware and IQ8 Bridge/RPC.

    Expected output (with MCU correlation validated by firmware and gateway):
        sequence_id: uint32
        joint_targets: six MJCF-radian values in contract order
        duration: seconds
        timeout: seconds

    You MUST:
    - send AI candidate action to STM32 using actual supported App Lab Bridge/RPC;
    - check returned MCU status and sequence ID;
    - forward only validated, scheduled actions;
    - handle heartbeat loss, MCU faults and calibration mapping.
    """
    raise MCUApprovalRequired('Real STM32H5F5 firmware/Bridge RPC is not implemented in this starter.')


class GatewaySession:
    """Persistent authenticated TCP control session; one connection per IQ8 gateway."""
    def __init__(self, host, token, port=5050):
        self.host, self.token, self.port = host, token, port
        self.sock = None
        self.stream = None

    def __enter__(self):
        self.sock=socket.create_connection((self.host,self.port),timeout=5)
        self.sock.settimeout(5)
        self.stream=self.sock.makefile('rb')
        hello=self._exchange({'type':'HELLO','token':self.token})
        if hello.get('type')!='WELCOME':
            self.__exit__(None,None,None)
            raise ConnectionError(f'Gateway authentication rejected: {hello}')
        return self

    def __exit__(self,*args):
        if self.stream:
            self.stream.close()
            self.stream=None
        if self.sock:
            self.sock.close()
            self.sock=None

    def _exchange(self,item):
        if not self.sock:raise ConnectionError('Gateway session closed')
        self.sock.sendall((json.dumps(item,separators=(',',':'))+'\n').encode('utf8'))
        frame=self.stream.readline(16_385)
        if not frame or len(frame)>16_384:
            raise ConnectionError('No valid response from simulation')
        return json.loads(frame)

    def send_approved_action(self, approved):
        """Only invoke with actual output of the MCU Bridge/RPC approval function."""
        action={'type':'ACTION',
                'sequence_id':approved['sequence_id'],
                'joint_targets':approved['joint_targets'],
                'duration':approved['duration'],
                'timeout':approved['timeout']}
        reply=self._exchange(action)
        if reply.get('type')!='ACK':
            raise RuntimeError(f'Action not accepted: {reply}')
        return reply

    def until_done(self, sequence_id, max_wait_s=15):
        """Keep the session alive and consume feedback until target/fault/timeout."""
        started=time.monotonic()
        while time.monotonic()-started<max_wait_s:
            state=self._exchange({'type':'GET_STATE'})
            if state.get('type')!='STATE':
                raise RuntimeError(f'Unexpected reply: {state}')
            status=state.get('status')
            if state.get('applied_sequence')==sequence_id and status=='DONE':
                return state
            if status in ('FAULT','WAITING_FOR_BOARD'):
                raise RuntimeError(f'Simulation execution stopped: {state.get("fault") or status}')
            time.sleep(.25)
        raise TimeoutError('Simulation did not report DONE within requested time')


if __name__=='__main__':
    # Fail closed. Connectivity-only checks are in connectivity_probe.py.
    read_mcu_approved_action()
