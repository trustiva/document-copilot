import { request } from './http'

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
}

