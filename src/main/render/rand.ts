/**
 * 种子化随机数（移植自 Python `random.Random`）。
 *
 * 不与 Python Mersenne Twister 逐位对齐，仅保证：
 * - 同 seed → 同输出序列（可复现）；
 * - gauss 分布形状与 Python 一致（Box-Muller + gauss_next 缓存，sigma==0 返回 mu）。
 *
 * Python `random.gauss`:
 *   x2pi = random() * 2π; g2rad = sqrt(-2 ln(1-random())); z = cos(x2pi)*g2rad; next = sin(x2pi)*g2rad
 */
const TWO_PI = Math.PI * 2

export class Rng {
  private state: number
  private gaussNext: number | null = null

  constructor(seed: number) {
    // mulberry32 要求 32 位无符号种子
    this.state = seed >>> 0
  }

  /** [0, 1) 均匀分布。 */
  random(): number {
    // mulberry32
    this.state |= 0
    this.state = (this.state + 0x6d2b79f5) | 0
    let t = Math.imul(this.state ^ (this.state >>> 15), 1 | this.state)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }

  gauss(mu: number, sigma: number): number {
    if (sigma === 0) return mu
    let z = this.gaussNext
    this.gaussNext = null
    if (z === null) {
      const x2pi = this.random() * TWO_PI
      const g2rad = Math.sqrt(-2.0 * Math.log(1.0 - this.random()))
      z = Math.cos(x2pi) * g2rad
      this.gaussNext = Math.sin(x2pi) * g2rad
    }
    return mu + z * sigma
  }
}

/** 用 crypto 生成一个 32 位种子（seed=null 时使用）。 */
export function randomSeed(): number {
  const buf = new Uint32Array(1)
  // 在 node 环境：crypto.getRandomValues 可用
  const g = globalThis as { crypto?: { getRandomValues: (b: Uint32Array) => Uint32Array } }
  if (g.crypto?.getRandomValues) {
    g.crypto.getRandomValues(buf)
    return buf[0]
  }
  return (Math.floor(Math.random() * 0x100000000)) >>> 0
}

export function makeRng(seed: number | null): Rng {
  return new Rng(seed === null ? randomSeed() : seed)
}
