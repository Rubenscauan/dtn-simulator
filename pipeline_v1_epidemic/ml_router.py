import joblib
import pandas as pd
import dtnsim.agent


class MLRouter(dtnsim.agent.Epidemic):
    """
    Igual ao Epidemic, mas decide com ML se cada forward vale a pena.
    """

    def __init__(self, scheduler, mobility, monitor, range_):
        super().__init__(
            scheduler=scheduler,
            mobility=mobility,
            monitor=monitor,
            range_=range_,
        )

        self.model = joblib.load("ml_router_model.pkl")
        self.feature_cols = joblib.load("ml_router_features.pkl")

        self.msg_forward_count = {}
        self.pair_count = {}
        self.msg_first_time = {}
        self.msg_receivers = {}
        self.origem_forward_count = 0

    def _msg_num(self, msg_id):
        return abs(hash(msg_id)) % 100000

    def _source_num(self):
        return 0

    def _build_features(self, neighbor, msg_id):
        now = self.scheduler.time
        origem = self.id_
        destino = neighbor.id_

        if msg_id not in self.msg_forward_count:
            self.msg_forward_count[msg_id] = 0

        if msg_id not in self.msg_first_time:
            self.msg_first_time[msg_id] = now

        if msg_id not in self.msg_receivers:
            self.msg_receivers[msg_id] = {origem}

        pair_key = (origem, destino)
        if pair_key not in self.pair_count:
            self.pair_count[pair_key] = 0

        row = {
            "tempo": now,
            "origem": origem,
            "destino": destino,
            "msg_num": self._msg_num(msg_id),
            "source_num": self._source_num(),
            "msg_forward_count_before": self.msg_forward_count[msg_id],
            "origem_forward_count_before": self.origem_forward_count,
            "destino_receive_count_before": 1 if destino in self.msg_receivers[msg_id] else 0,
            "pair_count_before": self.pair_count[pair_key],
            "msg_age": now - self.msg_first_time[msg_id],
            "unique_receivers_before": len(self.msg_receivers[msg_id]),
        }

        return pd.DataFrame([row], columns=self.feature_cols)

    def _register_forward(self, neighbor, msg_id):
        origem = self.id_
        destino = neighbor.id_
        pair_key = (origem, destino)

        self.msg_forward_count[msg_id] = self.msg_forward_count.get(msg_id, 0) + 1
        self.origem_forward_count += 1
        self.pair_count[pair_key] = self.pair_count.get(pair_key, 0) + 1

        if msg_id not in self.msg_receivers:
            self.msg_receivers[msg_id] = {origem}

        self.msg_receivers[msg_id].add(destino)

    def _ml_allows_forward(self, neighbor, msg_id):
        X = self._build_features(neighbor, msg_id)
        pred = self.model.predict(X)[0]
        return pred == 1

    def forward(self):
        """
        Mesmo fluxo do Epidemic, mas filtrando cada envio com ML.
        """
        encounters = self.encounters()

        for agent in encounters:
            for msg in self.pending_messages():
                # Evitar encaminhamento redundante para quem já tem a msg
                if msg in getattr(agent, "received", {}):
                    continue

                if not self._ml_allows_forward(agent, msg):
                    continue

                dst = self.msg_dst(msg)

                # Mantém a lógica do Epidemic
                if agent.id_ == dst:
                    self.sendmsg(agent, msg)
                    if msg in self.received:
                        del self.received[msg]
                    self.delivered[msg] += 1
                else:
                    self.sendmsg(agent, msg)

                self._register_forward(agent, msg)