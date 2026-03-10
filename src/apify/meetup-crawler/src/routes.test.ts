import { parseDateTimeRange } from './routes.js'
import { describe, expect, it } from 'vitest'

describe.skip('parse guestsContent', () => {
  it('should parse guests correctly', () => {
    const guestsContent = 'Vance Dekker, Felipe Rubio and 150 others, Vance Dekker, Felipe Rubio and 150 others'
    const guests = guestsContent.replace(/ and \d+ others/g, '').split(', ')
    expect(guests).toEqual(['Vance Dekker', 'Felipe Rubio', 'Vance Dekker', 'Felipe Rubio'])
  })
})

describe('parseTimeRange', () => {
  it('should parse time range correctly with HTML tags', () => {
    const datetime = 'Wednesday, January 15, 2025 <br> 5:30 PM to 8:30 PM EST'
    const { dateStart: timeStart, dateEnd: timeEnd } = parseDateTimeRange(datetime)
    expect(timeStart).toEqual(new Date('January 15, 2025 5:30 PM EST'))
    expect(timeEnd).toEqual(new Date('January 15, 2025 8:30 PM EST'))
  })

  it('should parse time range correctly with HTML comments', () => {
    const datetime = 'Saturday, January 18, 2025 1:00 PM<!-- --> to 2:30 PM<!-- --> <!-- -->EST'
    const { dateStart: timeStart, dateEnd: timeEnd } = parseDateTimeRange(datetime)
    expect(timeStart).toEqual(new Date('January 18, 2025 1:00 PM EST'))
    expect(timeEnd).toEqual(new Date('January 18, 2025 2:30 PM EST'))
  })

  it('should parse time range correctly with HTML comments 2', () => {
    const datetime = 'Thursday, January 16, 2025 at 6:00 PM<!-- --> to Thursday, January 16, 2025 at 8:00 PM<!-- --> <!-- -->EST'
    const { dateStart: timeStart, dateEnd: timeEnd } = parseDateTimeRange(datetime)
    expect(timeStart).toEqual(new Date('January 18, 2025 1:00 PM EST'))
    expect(timeEnd).toEqual(new Date('January 18, 2025 2:30 PM EST'))
  })

  it('should throw an error for invalid datetime format', () => {
    const datetime = 'Invalid datetime format'
    expect(() => parseDateTimeRange(datetime)).toThrowError()
  })
})
