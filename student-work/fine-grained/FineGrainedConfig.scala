// Requires the saved fine-grained/rocket-chip.patch before linking/building.
package chipyard

import org.chipsalliance.cde.config._
import freechips.rocketchip.rocket._

class WithFineGrainedDP extends RocketCoreConfig(_.copy(useFineGrainedDP = true))
class WithFineGrainedDot extends RocketCoreConfig(_.copy(useFineGrainedDot = true))

// Preserve every BaselineConfig parameter except the native DP feature gate.
class FineGrainedDPConfig extends Config(
  new WithFineGrainedDP ++
  new BaselineConfig)

class FineGrainedDotConfig extends Config(
  new WithFineGrainedDot ++
  new BaselineConfig)

// Defined for the S6 integration gate; S5 verifies each family independently.
class FineGrainedConfig extends Config(
  new WithFineGrainedDot ++
  new WithFineGrainedDP ++
  new BaselineConfig)
