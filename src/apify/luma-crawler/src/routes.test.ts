import { parseDateTimeRange } from './routes.js'
import { describe, expect, it } from 'vitest'

describe('parse guestsContent', () => {
  it('should parse guests correctly', () => {
    const guestsContent = 'Vance Dekker, Felipe Rubio and 150 others, Vance Dekker, Felipe Rubio and 150 others'
    const guests = guestsContent.replace(/ and \d+ others/g, '').split(', ')
    expect(guests).toEqual(['Vance Dekker', 'Felipe Rubio', 'Vance Dekker', 'Felipe Rubio'])
  })

  describe('parse guestsContent', () => {
    it('should parse guests correctly', () => {
      const guestsContent = 'Vance Dekker, Felipe Rubio and 150 others, Vance Dekker, Felipe Rubio and 150 others'
      const guests = guestsContent.replace(/ and \d+ others/g, '').split(', ')
      expect(guests).toEqual(['Vance Dekker', 'Felipe Rubio', 'Vance Dekker', 'Felipe Rubio'])
    })
  })

  describe('parseDateTimeRange', () => {
    it('should parse date and time range correctly and infer the current year', () => {
      const dateStr = 'Tuesday, January 14'
      const timeStr = '5:30 PM - 8:30 PM'
      const { dateStart, dateEnd } = parseDateTimeRange(dateStr, timeStr)

      const currentYear = new Date().getFullYear()

      expect(dateStart).toEqual(new Date(Date.parse(`Tuesday, January 14 5:30 PM, ${currentYear}`)))
      expect(dateEnd).toEqual(new Date(Date.parse(`Tuesday, January 14 8:30 PM, ${currentYear}`)))
    })

    it('should handle different time formats', () => {
      const dateStr = 'Wednesday, February 20'
      const timeStr = '10:00 AM - 2:00 PM'
      const { dateStart, dateEnd } = parseDateTimeRange(dateStr, timeStr)

      const currentYear = new Date().getFullYear()

      expect(dateStart).toEqual(new Date(Date.parse(`Wednesday, February 20 10:00 AM, ${currentYear}`)))
      expect(dateEnd).toEqual(new Date(Date.parse(`Wednesday, February 20 2:00 PM, ${currentYear}`)))
    })

    it('should parse date and time range correctly when the year is specified', () => {
      const dateStr = 'Thursday, December 25, 2026'
      const timeStr = '6:00 PM - 9:00 PM'
      const { dateStart, dateEnd } = parseDateTimeRange(dateStr, timeStr)

      expect(dateStart).toEqual(new Date(Date.parse('Thursday, December 25, 2026 6:00 PM')))
      expect(dateEnd).toEqual(new Date(Date.parse('Thursday, December 25, 2026 9:00 PM')))
    })
  })
})
