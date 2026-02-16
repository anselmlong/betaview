# Climbing Technique Evaluation by Means of Skeleton Video Stream Analysis

**Source:** Sensors 2023, 23(19), 8216
**URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC10574944/
**Authors:** (See original paper)

## Key Findings for BetaView

### Climbing Phases (from Testa et al.)
1. **Preparation** - climber sets up body, establishes position, sets feet to initiate standing-up action
2. **Reaching** - climber stands up to reach and grab next hold
3. **Stabilization** - climber adjusts and relaxes body after reaching hold

### Six Climbing Errors Modeled

#### 1. Decoupling (Preparation Phase)
- **Technique:** Energy-saving technique where the arm of the holding hand should be straight when feet are being set
- **Error Detection:** Elbow angle AND shoulder angle both < 150°

#### 2. Reaching Hand Supports (Reaching Phase)
- **Technique:** Supporting hand should stay on hold as long as possible before reaching
- **Error Detection:** Reaching takes longer than 1 second

#### 3. Weight Shift (Reaching Phase)
- **Technique:** Weight should shift onto leg opposite the supporting hand; knee shifts vertically in front of toe
- **Error Detection:** Climber stands while pulling with holding arm, knee never vertical in front of toe

#### 4. Both Feet Set (Reaching Phase)
- **Technique:** Both feet should be placed on wall during standing up action
- **Error Detection:** Only one foot has wall contact when standing up, other foot moves or hangs loose

#### 5. Shoulder Relaxing (Stabilization Phase)
- **Technique:** After gripping, arm should stretch and CoM should lower; hips approach perpendicular of holding hand
- **Error Detection:** After gripping, arm remains locked; elbow/shoulder angles < 150°

#### 6. Hip Close to Wall (Reaching Phase)
- **Technique:** Keep hips as close to wall as possible - results in efficient climbing as weight rests on toe holds
- **Error Detection:** Hip distance to wall exceeds reference by > 5cm

### Technical Approach
- Uses skeleton video stream analysis
- Finite state machine to track climbing phases
- Analyzes position and velocities of hands, feet, and hips
- Center of Mass (CoM) tracking
- Joint angle measurements

### Key Metrics Referenced
- Elbow angle threshold: 150°
- Shoulder angle threshold: 150°
- Reaching time threshold: 1 second
- Hip distance threshold: 5cm deviation from reference
