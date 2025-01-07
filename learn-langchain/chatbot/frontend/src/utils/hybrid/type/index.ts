export enum FlexResponeCode {
  OK,
  FAIL
}

export type FlexResponeHeader = {
  code: FlexResponeCode;
  message: string;
};

export type FlexRespone = {
  response: FlexResponeHeader;
};
