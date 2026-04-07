declare module 'react-signature-canvas' {
  import { Component } from 'react'

  interface SignatureCanvasProps {
    canvasProps?: React.CanvasHTMLAttributes<HTMLCanvasElement>
    clearOnResize?: boolean
    velocityFilterWeight?: number
    minWidth?: number
    maxWidth?: number
    minDistance?: number
    dotSize?: number | (() => number)
    penColor?: string
    backgroundColor?: string
    onBegin?: () => void
    onEnd?: () => void
  }

  export default class SignatureCanvas extends Component<SignatureCanvasProps> {
    clear(): void
    isEmpty(): boolean
    toDataURL(type?: string, encoderOptions?: number): string
    fromDataURL(
      dataURL: string,
      options?: { ratio?: number; width?: number; height?: number },
    ): void
    toData(): any[]
    fromData(data: any[]): void
    getCanvas(): HTMLCanvasElement
    getTrimmedCanvas(): HTMLCanvasElement
    off(): void
    on(): void
  }
}
