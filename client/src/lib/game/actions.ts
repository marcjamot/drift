export interface Action {
	type: string;
	data: Record<string, unknown>;
	seq: number;
	at: number;
	visible_to?: string[];
}
