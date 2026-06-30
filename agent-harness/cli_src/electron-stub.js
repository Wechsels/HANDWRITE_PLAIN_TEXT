// Electron stub for the headless render backend. The render pipeline never
// touches Electron when renderPages is called with save=false (the only Electron
// reference is inside saveOutputs, which is skipped). This stub lets the bundle
// load paths.ts without pulling in the real Electron module.
export const app = {
  isPackaged: false,
  getAppPath: () => process.cwd(),
  getPath: () => process.cwd()
}
export default { app }
