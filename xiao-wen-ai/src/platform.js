/**

 * 运行平台识别与存储适配（Web / PWA / Android App / Electron）。

 */

import { Capacitor } from '@capacitor/core'

export const Platform = {
  WEB: 'web',

  PWA: 'pwa',

  ANDROID: 'android',

  IOS: 'ios',

  ELECTRON: 'electron',
}

export function detectPlatform() {
  if (typeof window !== 'undefined' && window.electronAPI?.isElectron) {
    return Platform.ELECTRON
  }

  if (Capacitor.isNativePlatform()) {
    const native = Capacitor.getPlatform()

    if (native === 'android') return Platform.ANDROID

    if (native === 'ios') return Platform.IOS

    return Platform.WEB
  }

  if (typeof window !== 'undefined' && window.matchMedia('(display-mode: standalone)').matches) {
    return Platform.PWA
  }

  return Platform.WEB
}

export const platform = detectPlatform()

export const platformLabel =
  {
    [Platform.WEB]: 'Web',

    [Platform.PWA]: 'PWA',

    [Platform.ANDROID]: 'Android',

    [Platform.IOS]: 'iOS',

    [Platform.ELECTRON]: 'Electron',
  }[platform] || 'Web'

export const isNativeApp = Capacitor.isNativePlatform()

/** 存储：各端均用 localStorage（Electron 开发/打包页同源持久化） */

export const storage = {
  get(key) {
    return localStorage.getItem(key)
  },

  set(key, value) {
    localStorage.setItem(key, value)
  },
}
