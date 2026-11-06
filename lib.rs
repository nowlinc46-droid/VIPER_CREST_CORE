//! ====================================================================
//! VIPERCREST 2.0 - DETERMINISTIC EPISTEMIC STATE (RUST NO_STD)
//! Cartridge: SECURITY_IR | Zero Allocation | Compile-Time Provenance
//! ====================================================================
#![no_std]

#[derive(Copy, Clone, PartialEq, Eq, Debug)]
pub enum EpistemicState {
    Suspended { gaps: u8 },
    Bounded { observed: u8 },
    Sealed { observed: u8 },
}

pub struct AttestedPlantGovernor {
    pub state: EpistemicState,
    pub max_torque_nm: f32,
    pub is_tripped: bool,
    pub receipt_digest: [u8; 16],
}

pub const CURRENT_ATTESTED_STATE: AttestedPlantGovernor = AttestedPlantGovernor {
    state: EpistemicState::Bounded { observed: 8 },
    max_torque_nm: 80.0,
    is_tripped: false,
    receipt_digest: [0x4A, 0xC3, 0x93, 0x6D, 0x89, 0x15, 0xEF, 0x7F, 0x20, 0xB4, 0x74, 0xC6, 0x01, 0xF3, 0x44, 0x42],
};

impl AttestedPlantGovernor {
    #[inline(always)]
    pub const fn is_safe_to_actuate(&self) -> bool {
        match self.state {
            EpistemicState::Suspended { .. } => false,
            EpistemicState::Bounded { .. } | EpistemicState::Sealed { .. } => !self.is_tripped,
        }
    }
}