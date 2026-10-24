/**
 * What to say about a product's storage and memory.
 *
 * The catalogue is mixed: a laptop has both figures, a hair dryer has
 * neither, and the record of "neither" is the two columns being blank
 * rather than a zero. Printing what is there and leaving out what is not
 * keeps the interface from claiming that a dryer has 0 GB of memory, and
 * from showing a half-written line such as "2024, GB" beside a model name.
 */

export interface MemorySpec {
  storage_gb: string
  ram_gb: string
}

/**
 * Return the figures as the catalogue writes them: "512/18".
 *
 * Empty when the product has no figures, so that the caller can leave that
 * part of the line out entirely instead of printing nothing in it.
 */
export function memoryFigures(sku: MemorySpec): string {
  return [sku.storage_gb, sku.ram_gb].filter(Boolean).join('/')
}

/**
 * Return the storage with its unit: "512GB".
 *
 * Empty when the product has no storage.
 */
export function storageFigure(sku: MemorySpec): string {
  return sku.storage_gb ? `${sku.storage_gb}GB` : ''
}
