import { describe, it, expect } from 'vitest'
import { getWhatsAppBuyUrl, createWhatsAppBuyMessage, WHATSAPP_PHONE } from './whatsapp'

describe('WhatsApp Buy Feature', () => {
  const sampleProduct = {
    id: 'device-test-123',
    title: 'iPhone 15 Pro 256GB',
    price: { amount: 899.99, currency: 'USD' },
    condition: 'Excellent',
    grade: 'A',
    category_label: 'Smartphones',
  }

  it('targets the configured WhatsApp number +919471190089', () => {
    expect(WHATSAPP_PHONE).toBe('919471190089')
    const url = getWhatsAppBuyUrl(sampleProduct)
    expect(url).toContain('https://wa.me/919471190089')
  })

  it('builds a message containing product title, price, condition and ID', () => {
    const message = createWhatsAppBuyMessage(sampleProduct)
    expect(message).toContain('iPhone 15 Pro 256GB')
    expect(message).toContain('$899.99')
    expect(message).toContain('Excellent (Grade A)')
    expect(message).toContain('device-test-123')
    expect(message).toContain('Smartphones')
  })

  it('properly encodes the message into the URL query parameter', () => {
    const url = getWhatsAppBuyUrl(sampleProduct)
    const parsed = new URL(url)
    expect(parsed.hostname).toBe('wa.me')
    expect(parsed.pathname).toBe('/919471190089')
    const textParam = parsed.searchParams.get('text')
    expect(textParam).toContain('iPhone 15 Pro 256GB')
    expect(textParam).toContain('$899.99')
  })
})
