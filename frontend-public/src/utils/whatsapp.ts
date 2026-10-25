import { formatMoney } from '@/types/decision'

export const WHATSAPP_PHONE = '919471190089'

export interface WhatsAppProductDetails {
  id: string
  title: string
  price: { amount: number; currency?: string }
  condition?: string
  grade?: string
  category_label?: string
}

/**
 * Build a readable pre-filled inquiry message for WhatsApp.
 */
export function createWhatsAppBuyMessage(product: WhatsAppProductDetails): string {
  const parts = [
    `Hi, I want to buy this item from SecondRoute:`,
    ``,
    `*Product:* ${product.title}`,
    `*Price:* ${formatMoney(product.price.amount)}`,
  ]

  if (product.condition) {
    const gradeStr = product.grade ? ` (Grade ${product.grade})` : ''
    parts.push(`*Condition:* ${product.condition}${gradeStr}`)
  }

  if (product.category_label) {
    parts.push(`*Category:* ${product.category_label}`)
  }

  parts.push(`*Item ID:* ${product.id}`)
  parts.push(``)
  parts.push(`Is this device currently available?`)

  return parts.join('\n')
}

/**
 * Return the direct WhatsApp link for purchasing a listing.
 */
export function getWhatsAppBuyUrl(product: WhatsAppProductDetails): string {
  const message = createWhatsAppBuyMessage(product)
  return `https://wa.me/${WHATSAPP_PHONE}?text=${encodeURIComponent(message)}`
}
