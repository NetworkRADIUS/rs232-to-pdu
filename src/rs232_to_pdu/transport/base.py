"""
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

This software may not be redistributed in any form without the prior
written consent of InkBridge Networks.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.

Abstract base class for a command transport
"""

from abc import ABC, abstractmethod


class Transport(ABC):
    """
    Abstract class representing a method of transporting outlet state changes
    or retrievals
    """

    def __init__(self, outlets: list[str]):
        """

        Args:
            outlets: list of strings representing controllable outlets
        """
        self.outlets = outlets

    @abstractmethod
    async def outlet_state_get(self, outlet: str) -> tuple[bool, any]:
        """
        Abstract method for retrieving the state of an outlet
        Args:
            outlet: string representation of the outlet

        Returns:
            success bool, state of the outlet
        """

    @abstractmethod
    async def outlet_state_set(self, outlet: str, state: any) -> tuple[
        bool, any]:
        """
        Abstract method for setting the state of an outlet
        Args:
            outlet: string representation of the outlet
            state: desired state

        Returns:
            success bool, state of the outlet after sending request
        """
